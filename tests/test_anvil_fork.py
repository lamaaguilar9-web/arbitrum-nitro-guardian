"""
Arbitrum Nitro Guardian - Security Audit Suite (v3.1)
Covers real production code execution across all modules:
1. Production Risk Engine: AMM Algebra invariant breach detection & threat scoring.
2. Production Circuit Breaker: Least-privilege AccessControl (PAUSER_ROLE vs UNPAUSER_ROLE).
3. Production Circuit Breaker: 24h timeout transition strictly to EMERGENCY_WIND_DOWN.
4. Production Circuit Breaker: Dynamic P95 percentile EIP-1559 gas escalation.
5. Production Circuit Breaker: Autonomous mitigation dispatch & incident history logging.
6. Production Telemetry Sensor: Live Chainlink Sequencer status decoding & 3600s grace period.
7. Production Telemetry Sensor: Honest fallback with ZERO fabricated numbers when RPC fails.
8. Production Telemetry Sensor: Labeled static demo pool catalog & explicit KeyError on unknown pools.
"""

import os
import sys
sys_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if sys_root not in sys.path:
    sys.path.insert(0, sys_root)

import time
import unittest
from unittest.mock import patch
from telemetry_sensor import ArbitrumTelemetrySensor
from risk_engine import ArbitrumRiskEngine
from circuit_breaker import ArbitrumCircuitBreaker


class TestArbitrumAuditV3(unittest.TestCase):
    def setUp(self):
        self.sensor = ArbitrumTelemetrySensor()
        self.engine = ArbitrumRiskEngine()
        self.breaker = ArbitrumCircuitBreaker()

    def test_01_risk_engine_algebra_invariant_breach_detection(self):
        """
        A2-2: Tests production ArbitrumRiskEngine.evaluate_pool_state()
        Verifies constant product algebra invariant breach detection when reserves drain >30%.
        """
        baseline_pool = {
            "pool_name": "Camelot_WETH_ARB",
            "protocol": "Camelot DEX",
            "protocol_type": "AMM_ALGEBRA",
            "reserve0": 1000.0,
            "reserve1": 2000000.0,
            "tvl_usd": 4000000.0
        }
        # Simulated attack: sudden 35% reserve drain
        attack_pool = {
            "pool_name": "Camelot_WETH_ARB",
            "protocol": "Camelot DEX",
            "protocol_type": "AMM_ALGEBRA",
            "reserve0": 650.0,
            "reserve1": 1300000.0,
            "tvl_usd": 2600000.0
        }
        tx_context = {
            "flash_loan_borrow_usd": 15000000.0,
            "observed_slippage_pct": 14.5,
            "sequencer_delay_ms": 250.0
        }

        eval_res = self.engine.evaluate_pool_state(attack_pool, baseline_pool, tx_context)
        self.assertTrue(eval_res["accounting_invariant"]["invariant_breached"])
        self.assertEqual(eval_res["threat_level"], "CRITICAL_EXPLOIT")
        self.assertEqual(eval_res["action_recommended"], "TRIP_L2_CIRCUIT_BREAKER_IMMEDIATELY")
        self.assertTrue(eval_res["should_trip"])
        self.assertGreaterEqual(eval_res["threat_score"], 0.82)
        print("[*] Test 1 OK: Production ArbitrumRiskEngine accurately flags invariant breach.")

    def test_02_circuit_breaker_least_privilege_access_control(self):
        """
        A2-2: Tests production ArbitrumCircuitBreaker pause and unpause access control.
        Enforces least-privilege role boundaries: Sentinel bot has PAUSER_ROLE only,
        unauthorized caller reverts, and bot cannot unpause (reserved for Gnosis Safe).
        """
        pool = "0x84652a577c80da0e539958340081928001692804"
        bot = self.breaker.guardian_bot_address
        unauthorized_caller = "0x000000000000000000000000000000000000BEEF"
        governance_safe = self.breaker.gnosis_safe_governance

        # 1. Bot caller successfully pauses pool with PAUSER_ROLE
        pause_res = self.breaker.execute_mock_onchain_pause(pool, bot, "EXPLOIT_DETECTED")
        self.assertTrue(pause_res["success"])
        self.assertEqual(self.breaker.onchain_pool_status[pool], "EMERGENCY_PAUSED")

        # 2. Unauthorized caller cannot pause
        unauth_pause = self.breaker.execute_mock_onchain_pause(pool, unauthorized_caller, "MALICIOUS")
        self.assertFalse(unauth_pause["success"])
        self.assertIn("lacks required PAUSER_ROLE", unauth_pause["error"])

        # 3. Sentinel bot cannot unpause (least privilege)
        bot_unpause = self.breaker.execute_mock_onchain_unpause(pool, bot)
        self.assertFalse(bot_unpause["success"])
        self.assertIn("Caller lacks UNPAUSER_ROLE", bot_unpause["error"])

        # 4. Gnosis Safe governance can unpause
        gov_unpause = self.breaker.execute_mock_onchain_unpause(pool, governance_safe)
        self.assertTrue(gov_unpause["success"])
        self.assertEqual(self.breaker.onchain_pool_status[pool], "OPERATIONAL")
        print("[*] Test 2 OK: Production ArbitrumCircuitBreaker least-privilege access control verified.")

    def test_03_circuit_breaker_24h_timeout_transitions_to_wind_down(self):
        """
        A2-2: Tests production ArbitrumCircuitBreaker.evaluate_24h_timeout_state().
        Verifies that after 24 hours (86,400s), paused pool transitions to WIND_DOWN, never auto-unpausing.
        """
        pool = "0x84652a577c80da0e539958340081928001692804"
        self.breaker.execute_mock_onchain_pause(pool, self.breaker.guardian_bot_address, "TEST_PAUSE")

        # Within 24 hours: remains EMERGENCY_PAUSED
        state_12h = self.breaker.evaluate_24h_timeout_state(pool, elapsed_seconds=43200)
        self.assertEqual(state_12h, "EMERGENCY_PAUSED")

        # After 24 hours: enters EMERGENCY_WIND_DOWN
        state_25h = self.breaker.evaluate_24h_timeout_state(pool, elapsed_seconds=90000)
        self.assertEqual(state_25h, "EMERGENCY_WIND_DOWN")
        self.assertEqual(self.breaker.onchain_pool_status[pool], "EMERGENCY_WIND_DOWN")
        print("[*] Test 3 OK: Production ArbitrumCircuitBreaker 24h timeout to WIND_DOWN verified.")

    def test_04_dynamic_p95_gas_escalator(self):
        """
        Tests production ArbitrumCircuitBreaker.calculate_eip1559_gas().
        Overbids P95 mempool tip by +50% under extreme panic (threat >= 0.82).
        """
        gas_profile = self.breaker.calculate_eip1559_gas(
            threat_score=0.95,
            base_fee_gwei=25.0,
            mempool_p95_tip_gwei=50.0
        )
        self.assertEqual(gas_profile["priority_fee_gwei"], 75.0)
        self.assertEqual(gas_profile["escalation_tier"], "CRITICAL_P95_OVERBID_150PCT")
        self.assertTrue(gas_profile["flashbots_private_bundle"])
        print(f"[*] Test 4 OK: P95 Gas Escalator validated: +{gas_profile['priority_fee_gwei']} Gwei tip.")

    def test_05_process_telemetry_dispatch_and_incident_logging(self):
        """
        A2-2: Tests production ArbitrumCircuitBreaker.process_telemetry().
        Trips breaker upon critical evaluation, updates state, and records incident.
        """
        critical_eval = {
            "threat_score": 0.92,
            "threat_score_pct": 92.0,
            "threat_level": "CRITICAL_EXPLOIT",
            "pool_name": "Camelot_WETH_ARB",
            "protocol": "Camelot DEX",
            "pool_address": "0x84652a577c80da0e539958340081928001692804"
        }
        incident = self.breaker.process_telemetry(critical_eval)
        self.assertEqual(self.breaker.state, "TRIPPED_EMERGENCY_HALT")
        self.assertEqual(incident["event"], "CIRCUIT_BREAKER_TRIPPED")
        self.assertEqual(incident["action_executed"], "ARBITRUM_ONE_GLOBAL_EMERGENCY_PAUSE")
        self.assertIsNotNone(incident["contract_pause_tx_hash"])
        self.assertEqual(len(self.breaker.incident_history), 1)
        print("[*] Test 5 OK: Production ArbitrumCircuitBreaker telemetry processing and incident dispatch verified.")

    def test_06_chainlink_sequencer_status_live_query_and_grace_period(self):
        """
        A2-1 / A2-2: Tests production ArbitrumTelemetrySensor.get_chainlink_sequencer_status().
        Verifies on-chain parsing and 3600s grace period logic:
        - Sequencer DOWN (answer == 1) -> status DOWN, is_healthy False.
        - Sequencer restarted < 3600s ago -> status GRACE_PERIOD, is_healthy False.
        - Sequencer restarted >= 3600s ago -> status UP, is_healthy True.
        """
        now = int(time.time())

        # Scenario A: Sequencer is Down (answer = 1)
        # ABI hex for (roundId=1, answer=1, startedAt=now, updatedAt=now, answeredInRound=1)
        hex_down = "0x" + ("00" * 31 + "01") + ("00" * 31 + "01") + f"{now:064x}" + f"{now:064x}" + ("00" * 31 + "01")
        with patch.object(self.sensor, "_post_rpc", return_value=(hex_down, 15.0, "https://arb1.arbitrum.io/rpc")):
            res = self.sensor.get_chainlink_sequencer_status()
            self.assertEqual(res["status"], "DOWN")
            self.assertFalse(res["is_healthy"])
            self.assertEqual(res["answer"], 1)

        # Scenario B: Sequencer restarted 15 minutes ago (< 3600s grace period)
        started_recent = now - 900
        hex_grace = "0x" + ("00" * 31 + "01") + ("00" * 32) + f"{started_recent:064x}" + f"{now:064x}" + ("00" * 31 + "01")
        with patch.object(self.sensor, "_post_rpc", return_value=(hex_grace, 15.0, "https://arb1.arbitrum.io/rpc")):
            res = self.sensor.get_chainlink_sequencer_status()
            self.assertEqual(res["status"], "GRACE_PERIOD")
            self.assertFalse(res["is_healthy"])
            self.assertEqual(res["answer"], 0)
            self.assertGreater(res["grace_period_remaining_s"], 0)

        # Scenario C: Sequencer restarted 2 hours ago (>= 3600s grace period cleared)
        started_stable = now - 7200
        hex_up = "0x" + ("00" * 31 + "01") + ("00" * 32) + f"{started_stable:064x}" + f"{now:064x}" + ("00" * 31 + "01")
        with patch.object(self.sensor, "_post_rpc", return_value=(hex_up, 15.0, "https://arb1.arbitrum.io/rpc")):
            res = self.sensor.get_chainlink_sequencer_status()
            self.assertEqual(res["status"], "UP")
            self.assertTrue(res["is_healthy"])
            self.assertEqual(res["answer"], 0)
            self.assertEqual(res["grace_period_remaining_s"], 0)
        print("[*] Test 6 OK: Production ArbitrumTelemetrySensor Sequencer Uptime Feed & 3600s Grace Period verified.")

    def test_07_honest_fallback_zero_fake_numbers(self):
        """
        K-2 / A2-3 / A2-4: Fallback when all RPCs fail must report OFFLINE with ZERO fabricated numbers.
        Asserts rpc_latency_ms is None (A2-3) and base_fee_gwei is None (A2-4).
        """
        with patch.object(self.sensor, "_post_rpc", return_value=(None, None, "https://arb1.arbitrum.io/rpc")):
            summary = self.sensor.get_latest_block_summary()
            self.assertEqual(summary["status"], "OFFLINE")
            self.assertIsNone(summary["block_number"])
            self.assertIsNone(summary["tx_count"])
            self.assertIsNone(summary["gas_used"])
            self.assertIsNone(summary["gas_utilization_pct"])
            self.assertIsNone(summary["base_fee_gwei"])
            self.assertIsNone(summary["rpc_latency_ms"])
            self.assertEqual(summary["error"], "ALL_RPC_ENDPOINTS_FAILED")
        print("[*] Test 7 OK: Honest fallback verified - zero fabricated numbers.")

    def test_08_pool_catalog_labeled_static_demo(self):
        """
        K-2 / A2-5: Catalog pools must be explicitly labeled as static demo, not live streaming telemetry.
        Unknown pool name raises explicit KeyError.
        """
        pools = self.sensor.get_all_pools()
        self.assertGreater(len(pools), 0)
        for pool in pools:
            self.assertEqual(pool["catalog_type"], "CATÁLOGO ESTÁTICO DE DEMO — NO ES TELEMETRÍA")
            self.assertEqual(pool["telemetry_source"], "STATIC_CATALOG_ESTIMATE")

        # A2-5: Unknown pool must raise KeyError
        with self.assertRaises(KeyError):
            self.sensor.sample_monitored_pool("Non_Existent_Pool_Name")
        print("[*] Test 8 OK: Static demo pool catalog honest labeling & explicit KeyError on unknown pool verified.")


if __name__ == "__main__":
    unittest.main()
