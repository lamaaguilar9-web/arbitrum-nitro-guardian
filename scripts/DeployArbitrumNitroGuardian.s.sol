// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import '../contracts/ArbitrumNitroCircuitBreaker.sol';
import '../contracts/examples/ProtectedPoolLP.sol';

/**
 * @title DeployArbitrumNitroGuardianScript
 * @notice Script de despliegue y configuracion inicial institucional para Arbitrum One Mainnet.
 */
contract DeployArbitrumNitroGuardianScript {
    // Direcciones oficiales Arbitrum One (Chain ID: 42161)
    address public constant CANONICAL_SEQUENCER_FEED = 0xFdB631F5EE196F0ed6FAa767959853A9F217697D;
    address public constant GNOSIS_SAFE_GOVERNANCE = 0x1b793E4923774423457917228833983216892416;
    address public constant GUARDIAN_BOT = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    ArbitrumNitroCircuitBreaker public circuitBreaker;
    ProtectedPoolLP public protectedPool;

    function run() external {
        // 1. Despliegue de ArbitrumNitroCircuitBreaker
        circuitBreaker = new ArbitrumNitroCircuitBreaker(
            GNOSIS_SAFE_GOVERNANCE,
            GUARDIAN_BOT,
            CANONICAL_SEQUENCER_FEED
        );

        // 2. Despliegue del Pool protegido
        protectedPool = new ProtectedPoolLP(
            address(circuitBreaker),
            10_000 ether,
            30_000_000 ether
        );

        // 3. Autorizacion formal del Pool en el Circuit Breaker
        circuitBreaker.setPoolAuthorization(address(protectedPool), true);

        // 4. Registro de selectores de emergencia permitidos durante WIND_DOWN y Grace Period:
        // Selector 1: emergencyWithdrawProRata(uint256) -> 0xb9a071ef
        bytes4 emergencyWithdrawSelector = ProtectedPoolLP.emergencyWithdrawProRata.selector;
        circuitBreaker.setEmergencySelector(address(protectedPool), emergencyWithdrawSelector, true);

        // Selector 2: transfer(address,uint256) burn fallback (to == address(0)) o withdraw(uint256)
        bytes4 standardWithdrawSelector = bytes4(keccak256('withdraw(uint256)')); // 0x2e1a7d4d
        circuitBreaker.setEmergencySelector(address(protectedPool), standardWithdrawSelector, true);

        // Selector 3: burn(address,uint256) -> 0x9dc29fac
        bytes4 burnSelector = bytes4(keccak256('burn(address,uint256)')); // 0x9dc29fac
        circuitBreaker.setEmergencySelector(address(protectedPool), burnSelector, true);
    }
}
