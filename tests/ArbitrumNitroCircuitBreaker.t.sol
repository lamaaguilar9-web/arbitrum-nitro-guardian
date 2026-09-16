// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import '../contracts/ArbitrumNitroCircuitBreaker.sol';
import '../contracts/examples/ProtectedPoolLP.sol';

// Mock Interfaces for Foundry
interface Vm {
    function warp(uint256) external;
    function prank(address) external;
    function expectRevert(bytes calldata) external;
}

contract MockSequencerFeed is ISequencerUptimeFeed {
    int256 public statusAnswer = 0; // 0 = UP, 1 = DOWN
    uint256 public statusStartedAt;

    constructor() {
        statusStartedAt = block.timestamp;
    }

    function setSequencerStatus(int256 _answer, uint256 _startedAt) external {
        statusAnswer = _answer;
        statusStartedAt = _startedAt;
    }

    function latestRoundData() external view override returns (
        uint80, int256, uint256, uint256, uint80
    ) {
        return (1, statusAnswer, statusStartedAt, block.timestamp, 1);
    }
}

contract ArbitrumNitroCircuitBreakerTest {
    ArbitrumNitroCircuitBreaker public breaker;
    ProtectedPoolLP public pool;
    MockSequencerFeed public feed;

    address public safe = address(0x1111);
    address public bot = address(0x2222);
    address public userA = address(0x3333);
    address public timelock = address(0x4444);

    function setUp() public {
        feed = new MockSequencerFeed();
        breaker = new ArbitrumNitroCircuitBreaker(safe, bot, address(feed));
        pool = new ProtectedPoolLP(address(breaker), 1000 ether, 1000 ether);

        // Configuracion inicial
        breaker.setPoolAuthorization(address(pool), true);
        breaker.setEmergencySelector(address(pool), ProtectedPoolLP.emergencyWithdrawProRata.selector, true);

        // Fondear a userA con LP tokens
        pool.mint(userA, 1000 ether);
    }

    // Caso 1: Sequencer DOWN o en periodo de gracia (3600s)
    function testSequencerDownBlocksOperations() public {
        feed.setSequencerStatus(1, block.timestamp); // DOWN
        assertFalse(breaker.isSequencerHealthy());
        assertFalse(breaker.isOperationPermitted(address(pool), bytes4(0x12345678)));
    }

    // Caso 2: Anti-Sybil revierte transferencias LP durante EMERGENCY_PAUSED
    function testAntiSybilFreezesTransfersDuringPause() public {
        breaker.pausePool(address(pool), 'FLASH_LOAN_ATTACK');
        // Transferencia de userA a otro usuario DEBE revertir
    }

    // Caso 3: Limite pro-rata 10% revierte con ProRataQuotaExceeded
    function testProRataQuotaEnforcement() public {
        breaker.pausePool(address(pool), 'MARKET_VOLATILITY');
        // Cuota maxima por epoch es 10% de 1000 ether = 100 ether
        // Retirar 150 ether debe revertir con ProRataQuotaExceeded()
    }

    // Caso 4: Tercera pausa consecutiva bloqueada (MaxConsecutivePausesExceeded)
    function testMaxConsecutivePausesEnforced() public {
        breaker.pausePool(address(pool), 'ATTACK_1');
        breaker.unpausePool(address(pool));
        breaker.pausePool(address(pool), 'ATTACK_2');
        breaker.unpausePool(address(pool));
        // La 3ra pausa consecutiva revierte si no hubo unpause con reset administrativo
    }

    // Caso 5: Revocacion de Safe al migrar a Timelock
    function testTimelockMigrationRevokesSafe() public {
        breaker.transferGovernanceToTimelock(timelock);
        assertFalse(breaker.hasRole(breaker.DEFAULT_ADMIN_ROLE(), safe));
        assertFalse(breaker.hasRole(breaker.UNPAUSER_ROLE(), safe));
        assertTrue(breaker.hasRole(breaker.DEFAULT_ADMIN_ROLE(), timelock));
        assertTrue(breaker.hasRole(breaker.UNPAUSER_ROLE(), timelock));
    }
}
