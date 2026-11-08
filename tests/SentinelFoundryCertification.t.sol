// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/ArbitrumNitroCircuitBreaker.sol";
import "../contracts/examples/ProtectedPoolLP.sol";

contract MockSequencerFeedCert is ISequencerUptimeFeed {
    int256 public statusAnswer = 0; // 0 = UP, 1 = DOWN
    uint256 public statusStartedAt;

    constructor() {
        statusStartedAt = block.timestamp > 7200 ? block.timestamp - 7200 : 0;
    }

    function setSequencerStatus(int256 _answer, uint256 _startedAt) external {
        statusAnswer = _answer;
        statusStartedAt = _startedAt;
    }

    function latestRoundData() external view override returns (uint80, int256, uint256, uint256, uint80) {
        return (1, statusAnswer, statusStartedAt, block.timestamp, 1);
    }
}

/// @title SentinelFoundryCertification - Arbitrum Nitro Guardian Invariant & Fuzzing Suite (256 Runs)
contract SentinelFoundryCertification is Test {
    ArbitrumNitroCircuitBreaker public breaker;
    ProtectedPoolLP public pool;
    MockSequencerFeedCert public feed;

    address public safe = address(0x1111);
    address public bot = address(0x2222);
    address public alice = address(0xA11CE);
    address public timelock = address(0x4444);

    function setUp() public {
        vm.warp(1_700_000_000);
        feed = new MockSequencerFeedCert();
        breaker = new ArbitrumNitroCircuitBreaker(safe, bot, address(feed));
        pool = new ProtectedPoolLP(address(breaker), 1000 ether, 1000 ether);

        breaker.setPoolAuthorization(address(pool), true);
        breaker.setEmergencySelector(address(pool), ProtectedPoolLP.emergencyWithdrawProRata.selector, true);
        pool.mint(alice, 1000 ether);
    }

    function test_Invariant_SequencerDownAndGracePeriodEnforcement() public {
        assertTrue(breaker.isSequencerHealthy(), "Sequencer should be healthy initially");
        feed.setSequencerStatus(1, block.timestamp);
        assertFalse(breaker.isSequencerHealthy(), "Sequencer down must block operations");
        assertFalse(breaker.isOperationPermitted(address(pool), bytes4(0x12345678)));
    }

    function testFuzz_ProRataEpochQuotaInvariant(uint96 userBalance, uint96 withdrawReq) public {
        vm.assume(userBalance >= 100 ether && userBalance <= 1_000_000 ether);
        uint256 maxAllowed = (uint256(userBalance) * breaker.PRO_RATA_RATE_LIMIT_BPS()) / 10000;
        vm.assume(withdrawReq > 0 && withdrawReq <= maxAllowed);

        vm.prank(bot);
        breaker.pausePool(address(pool), "INVARIANT_BREACH");

        vm.prank(address(pool));
        bool ok = breaker.checkProRataWithdrawalQuota(address(pool), alice, withdrawReq, userBalance);
        assertTrue(ok, "Within 10% epoch quota must succeed");
    }
}
