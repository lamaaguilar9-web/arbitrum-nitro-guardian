// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ArbitrumNitroCircuitBreaker
 * @notice Institutional-Grade Asymmetric Emergency Pause Sentinel for Arbitrum One (Nitro).
 * @dev Implements OpenZeppelin AccessControl and Pausable patterns.
 * 
 * SECURITY ARCHITECTURE & PRIVILEGE SEGREGATION:
 * 1. ASYMMETRIC CONTROL:
 *    - PAUSER_ROLE: Granted to automated Arbitrum Nitro Guardian Agent. Can ONLY trigger granular pauses.
 *    - UNPAUSER_ROLE: Strictly granted to Gnosis Safe Multisig (DAO / SecOps Governance).
 *    - DEFAULT_ADMIN_ROLE: Strictly granted to Gnosis Safe Multisig.
 * 2. PRINCIPLE OF LEAST PRIVILEGE:
 *    - This contract contains NO fund transfer, withdrawal, or token custody logic.
 *    - Private key compromise of the guardian agent CANNOT drain protocols or misappropriate assets.
 * 3. FALSE-POSITIVE MITIGATION:
 *    - Implements MAX_PAUSE_DURATION safety bounds to prevent indefinite denial of service.
 */

contract ArbitrumNitroCircuitBreaker {
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant PAUSER_ROLE = keccak256('PAUSER_ROLE');
    bytes32 public constant UNPAUSER_ROLE = keccak256('UNPAUSER_ROLE');

    address public immutable gnosisSafeGovernance;
    address public immutable guardianBot;
    
    mapping(address => bool) private _pausedPools;
    mapping(address => uint256) public poolPausedTimestamp;
    mapping(address => string) public lastPauseReason;

    uint256 public constant MAX_PAUSE_DURATION = 24 hours;
    mapping(bytes32 => mapping(address => bool)) private _roles;

    event PoolEmergencyPaused(address indexed pool, address indexed caller, string reason, uint256 timestamp);
    event PoolEmergencyUnpaused(address indexed pool, address indexed caller, uint256 timestamp);
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);

    modifier onlyRole(bytes32 role) {
        require(_roles[role][msg.sender], 'CircuitBreaker: caller lacks required role');
        _;
    }

    constructor(address _governanceSafe, address _botAddress) {
        require(_governanceSafe != address(0), 'Invalid governance safe address');
        require(_botAddress != address(0), 'Invalid guardian bot address');

        gnosisSafeGovernance = _governanceSafe;
        guardianBot = _botAddress;

        _roles[DEFAULT_ADMIN_ROLE][_governanceSafe] = true;
        _roles[UNPAUSER_ROLE][_governanceSafe] = true;
        _roles[PAUSER_ROLE][_botAddress] = true;

        emit RoleGranted(DEFAULT_ADMIN_ROLE, _governanceSafe, msg.sender);
        emit RoleGranted(UNPAUSER_ROLE, _governanceSafe, msg.sender);
        emit RoleGranted(PAUSER_ROLE, _botAddress, msg.sender);
    }

    function pausePool(address pool, string calldata reason) external onlyRole(PAUSER_ROLE) {
        require(pool != address(0), 'Invalid pool address');
        require(!_pausedPools[pool], 'Pool already paused');

        _pausedPools[pool] = true;
        poolPausedTimestamp[pool] = block.timestamp;
        lastPauseReason[pool] = reason;

        emit PoolEmergencyPaused(pool, msg.sender, reason, block.timestamp);
    }

    function unpausePool(address pool) external onlyRole(UNPAUSER_ROLE) {
        require(pool != address(0), 'Invalid pool address');
        require(_pausedPools[pool], 'Pool is not paused');

        _pausedPools[pool] = false;
        delete poolPausedTimestamp[pool];
        delete lastPauseReason[pool];

        emit PoolEmergencyUnpaused(pool, msg.sender, block.timestamp);
    }

    function isPoolOperational(address pool) external view returns (bool) {
        if (!_pausedPools[pool]) {
            return true;
        }
        if (block.timestamp > poolPausedTimestamp[pool] + MAX_PAUSE_DURATION) {
            return true;
        }
        return false;
    }

    function hasRole(bytes32 role, address account) external view returns (bool) {
        return _roles[role][account];
    }
}
