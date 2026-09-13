// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IArbitrumNitroCircuitBreaker
 * @notice Standard interface for the Arbitrum Nitro Circuit Breaker.
 */
interface IArbitrumNitroCircuitBreaker {
    event PoolEmergencyPaused(address indexed pool, address indexed caller, string reason, uint256 timestamp);
    event PoolEmergencyUnpaused(address indexed pool, address indexed caller, uint256 timestamp);

    function pausePool(address pool, string calldata reason) external;
    function unpausePool(address pool) external;
    function isPoolOperational(address pool) external view returns (bool);
    function hasRole(bytes32 role, address account) external view returns (bool);
    function poolPausedTimestamp(address pool) external view returns (uint256);
    function lastPauseReason(address pool) external view returns (string memory);
}\n