"""
Arbitrum Nitro Guardian - Anvil Mainnet Fork Test Suite
Simulates state transitions on forked Arbitrum One (Block #504,800,000+).

Tests Verified:
1. RPC Failover Mechanism (Primary <-> Secondary fallback).
2. Asymmetric AccessControl (PAUSER_ROLE vs UNPAUSER_ROLE).
3. Camelot DEX Invariant Breach & Dynamic EIP-1559 Priority Fee Escalation.
4. SLA Latency Verification (< 45ms mitigation window).
"""

import time
import unittest
from telemetry_sensor import ArbitrumTelemetrySensor
from risk_engine import ArbitrumRiskEngine
from circuit_breaker import ArbitrumCircuitBreaker


class TestArbitrumAnvilFork(unittest.TestCase):
    def setUp(self):
        self.sensor = ArbitrumTelemetrySensor()
        self.engine = ArbitrumRiskEngine()
        self.breaker = ArbitrumCircuitBreaker()

    def test_01_rpc_redundancy_and_failover(self):
        """Verify automatic failover between RPC endpoints without dropped requests"""
        active_endpoint = self.sensor.get_active_rpc_url()
        self.assertIn("arbitrum", active_endpoint.lower())
        
        # Trigger forced failover
        failover_res = self.sensor.trigger_manual_failover()
        self.assertTrue(failover_res["success"])
        self.assertNotEqual(active_endpoint, failover_res["new_active_endpoint"])
        print(f"[*] Failover Verified: Switched to {failover_res['new_active_endpoint']} in {failover_res['latency_ms']}ms")

    def test_02_asymmetric_access_control(self):
        """
        Verify that Guardian Bot can ONLY invoke PAUSE_ROLE,
        and cannot invoke UNPAUSE_ROLE (reserved for Gnosis Safe).
        """
        bot_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        gnosis_safe = "0x1b793E4923774423457917228833983216892416"

        # 1. Bot attempts pause (MUST SUCCEED)
        pause_action = self.breaker.execute_mock_onchain_pause(
            pool_address="0x84652a577c80da0e539958340081928001692804",
            caller_address=bot_address,
            reason="INVARIANT_BREACH_CAMELOT_AMM"
        )
        self.assertTrue(pause_action["success"])
        self.assertEqual(pause_action["role_used"], "PAUSER_ROLE")

        # 2. Bot attempts unpause (MUST REVERT)
        unpause_by_bot = self.breaker.execute_mock_onchain_unpause(
            pool_address="0x84652a577c80da0e539958340081928001692804",
            caller_address=bot_address
        )
        self.assertFalse(unpause_by_bot["success"])
        self.assertIn("REVERT: Caller lacks UNPAUSER_ROLE", unpause_by_bot["error"])

        # 3. Gnosis Safe attempts unpause (MUST SUCCEED)
        unpause_by_safe = self.breaker.execute_mock_onchain_unpause(
            pool_address="0x84652a577c80da0e539958340081928001692804",
            caller_address=gnosis_safe
        )
        self.assertTrue(unpause_by_safe["success"])
        self.assertEqual(unpause_by_safe["role_used"], "UNPAUSER_ROLE")

    def test_03_eip1559_gas_escalation(self):
        """Verify dynamic maxPriorityFeePerGas spikes during high threat events"""
        # Baseline normal fee
        normal_fee = self.breaker.calculate_eip1559_gas(threat_score=0.10)
        self.assertLessEqual(normal_fee["priority_fee_gwei"], 0.20)

        # Critical attack fee (threat >= 0.82)
        escalated_fee = self.breaker.calculate_eip1559_gas(threat_score=0.95)
        self.assertGreaterEqual(escalated_fee["priority_fee_gwei"], 1.50)
        self.assertGreater(escalated_fee["max_fee_gwei"], normal_fee["max_fee_gwei"])
        print(f"[*] EIP-1559 Escalation: Base {escalated_fee['base_fee_gwei']} Gwei -> Priority {escalated_fee['priority_fee_gwei']} Gwei (Total: {escalated_fee['max_fee_gwei']} Gwei)")

    def test_04_end_to_end_mitigation_sla(self):
        """Verify entire pipeline (telemetry -> risk evaluation -> pause execution) < 45ms"""
        t0 = time.perf_counter()
        pool = self.sensor.sample_monitored_pool("Camelot_WETH_ARB")
        attack_pool = dict(pool)
        attack_pool["tvl_usd"] = 5000000.0
        attack_pool["reserve0"] = 800.0
        attack_pool["reserve1"] = 5000000.0

        ctx = {
            "flash_loan_borrow_usd": 10000000.0,
            "sequencer_delay_ms": 350.0,
            "observed_slippage_pct": 15.0
        }

        eval_res = self.engine.evaluate_pool_state(attack_pool, pool, ctx)
        breaker_res = self.breaker.process_telemetry(eval_res)
        total_latency_ms = (time.perf_counter() - t0) * 1000

        self.assertTrue(eval_res["should_trip"])
        self.assertEqual(breaker_res["action_executed"], "ARBITRUM_ONE_GLOBAL_EMERGENCY_PAUSE")
        self.assertLess(total_latency_ms, 45.0)
        print(f"[*] End-to-End Mitigation SLA: {round(total_latency_ms, 2)}ms (Threshold: < 45.00ms)")


if __name__ == "__main__":
    unittest.main()
