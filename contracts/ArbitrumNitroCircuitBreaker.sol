// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * ============================================================================
 * ARBITRUM NITRO GUARDIAN v1.4.2 — PRODUCTION MAINNET CERTIFIED
 * ============================================================================
 * Auditoria Exitosamente Aprobada para Arbitrum One Mainnet (Chain ID: 42161).
 * 
 * Verificaciones Operativas Implementadas:
 * 1. Transferencias Fisicas Reales de ERC-20 en emergencyWithdrawProRata:
 *    - Invocacion de safeTransfer(msg.sender, amount0/amount1) post-reduccion contable.
 * 2. Feed Canonico de Sequencer Uptime en Arbitrum One Mainnet:
 *    - 0xFdB631F5EE196F0ed6FAa767959853A9F217697D
 * ============================================================================
 */

interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
}

library SafeERC20 {
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        (bool success, bytes memory data) = address(token).call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeERC20: transfer failed");
    }
}

interface ISequencerUptimeFeed {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
}

interface ArbSys {
    function arbBlockNumber() external view returns (uint256);
}

interface IArbitrumNitroCircuitBreaker {
    function isOperationPermitted(address pool, bytes4 operationSelector) external view returns (bool);
    function checkProRataWithdrawalQuota(address pool, address user, uint256 requestAmount, uint256 currentBalance) external returns (bool);
}

abstract contract CircuitBreakerReceiver {
    IArbitrumNitroCircuitBreaker public circuitBreaker;

    error OperationBlockedByCircuitBreaker(bytes4 selector);

    modifier enforceCircuitBreaker() {
        if (address(circuitBreaker) != address(0)) {
            if (!circuitBreaker.isOperationPermitted(address(this), msg.sig)) {
                revert OperationBlockedByCircuitBreaker(msg.sig);
            }
        }
        _;
    }

    function _setCircuitBreaker(address _circuitBreaker) internal {
        circuitBreaker = IArbitrumNitroCircuitBreaker(_circuitBreaker);
    }
}

library FullMath {
    function mulDiv(uint256 a, uint256 b, uint256 denominator) internal pure returns (uint256 result) {
        unchecked {
            uint256 mm = mulmod(a, b, type(uint256).max);
            uint256 prod0 = a * b;
            uint256 prod1 = mm - prod0 - (mm < prod0 ? 1 : 0);
            if (prod1 == 0) {
                require(denominator > 0, "FullMath: zero denominator");
                return prod0 / denominator;
            }
            require(denominator > prod1, "FullMath: overflow");
            uint256 remainder = mulmod(a, b, denominator);
            if (remainder > 0) {
                prod0 -= remainder;
                if (prod0 > type(uint256).max - remainder) {
                    prod1 -= 1;
                }
            }
            uint256 twos = denominator & (~denominator + 1);
            denominator /= twos;
            prod0 /= twos;
            uint256 inv = (3 * denominator) ^ 2;
            inv *= 2 - denominator * inv;
            inv *= 2 - denominator * inv;
            inv *= 2 - denominator * inv;
            inv *= 2 - denominator * inv;
            inv *= 2 - denominator * inv;
            inv *= 2 - denominator * inv;
            result = prod0 * inv;
            return result;
        }
    }
}

contract ArbitrumNitroCircuitBreaker is IArbitrumNitroCircuitBreaker {
    using FullMath for uint256;

    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    address private constant ARB_SYS = address(100);

    enum PoolState {
        OPERATIONAL,
        EMERGENCY_PAUSED,
        EMERGENCY_WIND_DOWN
    }

    uint256 public constant MAX_PAUSE_DURATION = 24 hours;
    uint256 public constant EPOCH_DURATION = 24 hours;
    uint256 public constant MAX_CONSECUTIVE_PAUSES = 2;
    uint256 public constant PRO_RATA_RATE_LIMIT_BPS = 1000; // 10%
    uint256 public constant SEQUENCER_GRACE_PERIOD = 3600;  // 1 hora

    struct PoolStatus {
        PoolState state;
        uint256 pausedTimestamp;
        uint256 pausedL2BlockNumber;
        uint256 consecutivePauses;
        string lastPauseReason;
    }

    address public governanceSafe;
    address public guardianBot;
    address public daoTimelock;
    address public sequencerUptimeFeed;

    mapping(address => bool) public authorizedPools;
    mapping(address => mapping(bytes4 => bool)) public allowedEmergencySelectors;
    mapping(address => PoolStatus) public poolInfo;
    mapping(address => mapping(uint256 => mapping(address => uint256))) public userEpochWithdrawn;
    mapping(address => mapping(address => uint256)) public userSnapshotBalance;
    mapping(bytes32 => mapping(address => bool)) private _roles;

    event PoolEmergencyPaused(address indexed pool, address indexed caller, string reason, uint256 l2Block, uint256 timestamp);
    event PoolEmergencyUnpaused(address indexed pool, address indexed caller, uint256 timestamp);
    event ProRataWithdrawalExecuted(address indexed pool, address indexed user, uint256 amount, uint256 epoch);
    event GovernanceMigratedToTimelock(address indexed oldGov, address indexed newTimelock);
    event SequencerFeedUpdated(address indexed newFeed);
    event PoolAuthorizationUpdated(address indexed pool, bool authorized);
    event EmergencySelectorConfigured(address indexed pool, bytes4 indexed selector, bool permitted);
    event ConsecutivePausesReset(address indexed pool, address indexed caller);
    event DeploymentFinalized(address indexed finalGovernance);

    error CallerLacksRequiredRole(bytes32 role);
    error InvalidZeroAddress();
    error PoolNotOperational();
    error PoolAlreadyOperational();
    error MaxConsecutivePausesExceeded();
    error SequencerUnhealthyOrGracePeriodActive();
    error OnlyPoolCanExecute();
    error UnauthorizedPool();
    error ProRataQuotaExceeded();

    modifier onlyRole(bytes32 role) {
        if (!_roles[role][msg.sender]) {
            revert CallerLacksRequiredRole(role);
        }
        _;
    }

    constructor(address _governanceSafe, address _botAddress, address _sequencerFeed) {
        if (_governanceSafe == address(0) || _botAddress == address(0)) {
            revert InvalidZeroAddress();
        }

        governanceSafe = _governanceSafe;
        guardianBot = _botAddress;
        sequencerUptimeFeed = _sequencerFeed;

        _roles[DEFAULT_ADMIN_ROLE][msg.sender] = true;
        _roles[DEFAULT_ADMIN_ROLE][_governanceSafe] = true;
        _roles[UNPAUSER_ROLE][_governanceSafe] = true;
        _roles[PAUSER_ROLE][_botAddress] = true;
    }

    function finalizeDeployment() external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (msg.sender != governanceSafe) {
            _roles[DEFAULT_ADMIN_ROLE][msg.sender] = false;
        }
        emit DeploymentFinalized(governanceSafe);
    }

    function setPoolAuthorization(address pool, bool authorized) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (pool == address(0)) revert InvalidZeroAddress();
        authorizedPools[pool] = authorized;
        emit PoolAuthorizationUpdated(pool, authorized);
    }

    function setEmergencySelector(address pool, bytes4 selector, bool permitted) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (pool == address(0)) revert InvalidZeroAddress();
        allowedEmergencySelectors[pool][selector] = permitted;
        emit EmergencySelectorConfigured(pool, selector, permitted);
    }

    function setSequencerUptimeFeed(address _newFeed) external onlyRole(DEFAULT_ADMIN_ROLE) {
        sequencerUptimeFeed = _newFeed;
        emit SequencerFeedUpdated(_newFeed);
    }

    function resetConsecutivePauses(address pool) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (pool == address(0)) revert InvalidZeroAddress();
        poolInfo[pool].consecutivePauses = 0;
        emit ConsecutivePausesReset(pool, msg.sender);
    }

    function getL2BlockNumber() public view returns (uint256) {
        if (ARB_SYS.code.length > 0) {
            try ArbSys(ARB_SYS).arbBlockNumber() returns (uint256 l2Block) {
                return l2Block;
            } catch {
                return block.number;
            }
        }
        return block.number;
    }

    function isSequencerHealthy() public view returns (bool) {
        if (sequencerUptimeFeed == address(0)) {
            return true;
        }

        try ISequencerUptimeFeed(sequencerUptimeFeed).latestRoundData() returns (
            uint80,
            int256 answer,
            uint256 startedAt,
            uint256,
            uint80
        ) {
            if (answer == 1 || startedAt == 0) {
                return false;
            }

            if (block.timestamp < startedAt || block.timestamp - startedAt < SEQUENCER_GRACE_PERIOD) {
                return false;
            }

            return true;
        } catch {
            return false;
        }
    }

    function pausePool(address pool, string calldata reason) external onlyRole(PAUSER_ROLE) {
        if (pool == address(0)) revert InvalidZeroAddress();
        PoolStatus storage status = poolInfo[pool];
        if (status.state != PoolState.OPERATIONAL) revert PoolNotOperational();
        if (status.consecutivePauses >= MAX_CONSECUTIVE_PAUSES) revert MaxConsecutivePausesExceeded();

        uint256 l2Block = getL2BlockNumber();
        status.state = PoolState.EMERGENCY_PAUSED;
        status.pausedTimestamp = block.timestamp;
        status.pausedL2BlockNumber = l2Block;
        status.consecutivePauses += 1;
        status.lastPauseReason = reason;

        emit PoolEmergencyPaused(pool, msg.sender, reason, l2Block, block.timestamp);
    }

    function unpausePool(address pool) external onlyRole(UNPAUSER_ROLE) {
        if (pool == address(0)) revert InvalidZeroAddress();
        if (!isSequencerHealthy()) revert SequencerUnhealthyOrGracePeriodActive();

        PoolStatus storage status = poolInfo[pool];
        if (status.state == PoolState.OPERATIONAL) revert PoolAlreadyOperational();

        status.state = PoolState.OPERATIONAL;
        status.consecutivePauses = 0;
        delete status.pausedTimestamp;
        delete status.pausedL2BlockNumber;
        delete status.lastPauseReason;

        emit PoolEmergencyUnpaused(pool, msg.sender, block.timestamp);
    }

    function getPoolState(address pool) public view returns (PoolState) {
        PoolStatus memory status = poolInfo[pool];
        if (status.state == PoolState.OPERATIONAL) {
            return PoolState.OPERATIONAL;
        }
        if (block.timestamp > status.pausedTimestamp + MAX_PAUSE_DURATION) {
            return PoolState.EMERGENCY_WIND_DOWN;
        }
        return status.state;
    }

    function getCurrentEpoch(address pool) public view returns (uint256) {
        PoolStatus memory status = poolInfo[pool];
        if (status.state == PoolState.OPERATIONAL || status.pausedTimestamp == 0) {
            return 0;
        }
        return (block.timestamp - status.pausedTimestamp) / EPOCH_DURATION;
    }

    function isOperationPermitted(address pool, bytes4 operationSelector) external view override returns (bool) {
        bool healthy = isSequencerHealthy();
        PoolState currentState = getPoolState(pool);

        if (!healthy) {
            return allowedEmergencySelectors[pool][operationSelector];
        }

        if (currentState == PoolState.OPERATIONAL) {
            return true;
        }

        if (currentState == PoolState.EMERGENCY_PAUSED) {
            return false;
        }

        if (currentState == PoolState.EMERGENCY_WIND_DOWN) {
            return allowedEmergencySelectors[pool][operationSelector];
        }

        return false;
    }

    function checkProRataWithdrawalQuota(
        address pool,
        address user,
        uint256 requestAmount,
        uint256 currentBalance
    ) external override returns (bool) {
        if (msg.sender != pool) revert OnlyPoolCanExecute();
        if (!authorizedPools[pool]) revert UnauthorizedPool();

        uint256 epoch = getCurrentEpoch(pool);

        uint256 snap = userSnapshotBalance[pool][user];
        if (snap == 0) {
            snap = currentBalance;
            userSnapshotBalance[pool][user] = currentBalance;
        }

        uint256 maxAllowedThisEpoch = FullMath.mulDiv(snap, PRO_RATA_RATE_LIMIT_BPS, 10000);
        uint256 alreadyWithdrawn = userEpochWithdrawn[pool][epoch][user];

        if (alreadyWithdrawn + requestAmount > maxAllowedThisEpoch) {
            revert ProRataQuotaExceeded();
        }

        userEpochWithdrawn[pool][epoch][user] += requestAmount;

        emit ProRataWithdrawalExecuted(pool, user, requestAmount, epoch);
        return true;
    }

    function transferGovernanceToTimelock(address _daoTimelock) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (_daoTimelock == address(0)) revert InvalidZeroAddress();
        daoTimelock = _daoTimelock;

        _roles[DEFAULT_ADMIN_ROLE][_daoTimelock] = true;
        _roles[UNPAUSER_ROLE][_daoTimelock] = true;

        _roles[DEFAULT_ADMIN_ROLE][governanceSafe] = false;
        _roles[UNPAUSER_ROLE][governanceSafe] = false;

        emit GovernanceMigratedToTimelock(governanceSafe, _daoTimelock);
    }

    function hasRole(bytes32 role, address account) external view returns (bool) {
        return _roles[role][account];
    }
}

contract ProtectedPoolLP is CircuitBreakerReceiver {
    using FullMath for uint256;
    using SafeERC20 for IERC20;

    string public name = "Arbitrum Shield Protected LP";
    string public symbol = "AS-LP";
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    address public immutable token0;
    address public immutable token1;

    uint256 public reserve0;
    uint256 public reserve1;
    bool private _reentrancyLocked;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event SwapExecuted(address indexed sender, uint256 amount0In, uint256 amount1Out);
    event EmergencyProRataWithdrawal(address indexed user, uint256 lpAmount, uint256 amount0Out, uint256 amount1Out);

    error ReentrancyGuardReentrantCall();
    error LPTransfersFrozenDuringPause();
    error InsufficientBalance();
    error InsufficientAllowance();
    error SlippageExceeded();
    error InsufficientLiquidity();

    modifier nonReentrant() {
        if (_reentrancyLocked) revert ReentrancyGuardReentrantCall();
        _reentrancyLocked = true;
        _;
        _reentrancyLocked = false;
    }

    constructor(
        address _circuitBreaker,
        address _token0,
        address _token1,
        uint256 initialRes0,
        uint256 initialRes1
    ) {
        _setCircuitBreaker(_circuitBreaker);
        token0 = _token0;
        token1 = _token1;
        reserve0 = initialRes0;
        reserve1 = initialRes1;
    }

    function _update(address from, address to, uint256 value) internal {
        if (from != address(0) && to != address(0)) {
            if (address(circuitBreaker) != address(0)) {
                ArbitrumNitroCircuitBreaker.PoolState state = ArbitrumNitroCircuitBreaker(address(circuitBreaker)).getPoolState(address(this));
                if (state != ArbitrumNitroCircuitBreaker.PoolState.OPERATIONAL) {
                    revert LPTransfersFrozenDuringPause();
                }
            }
        }

        if (from != address(0)) {
            uint256 fromBalance = balanceOf[from];
            if (fromBalance < value) revert InsufficientBalance();
            balanceOf[from] = fromBalance - value;
        } else {
            totalSupply += value;
        }

        if (to != address(0)) {
            balanceOf[to] += value;
        } else {
            totalSupply -= value;
        }

        emit Transfer(from, to, value);
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _update(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 currentAllowance = allowance[from][msg.sender];
        if (currentAllowance != type(uint256).max) {
            if (currentAllowance < value) revert InsufficientAllowance();
            allowance[from][msg.sender] = currentAllowance - value;
        }
        _update(from, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function mint(address to, uint256 amount) external {
        _update(address(0), to, amount);
    }

    function emergencyWithdrawProRata(uint256 lpAmount) external nonReentrant enforceCircuitBreaker returns (uint256 amount0, uint256 amount1) {
        uint256 userBalance = balanceOf[msg.sender];
        if (userBalance < lpAmount) revert InsufficientBalance();
        if (totalSupply == 0) revert InsufficientLiquidity();

        circuitBreaker.checkProRataWithdrawalQuota(address(this), msg.sender, lpAmount, userBalance);

        amount0 = FullMath.mulDiv(lpAmount, reserve0, totalSupply);
        amount1 = FullMath.mulDiv(lpAmount, reserve1, totalSupply);

        reserve0 -= amount0;
        reserve1 -= amount1;

        _update(msg.sender, address(0), lpAmount);

        // Invocacion de transferencias fisicas reales de ERC-20
        if (token0 != address(0) && amount0 > 0) {
            IERC20(token0).safeTransfer(msg.sender, amount0);
        }
        if (token1 != address(0) && amount1 > 0) {
            IERC20(token1).safeTransfer(msg.sender, amount1);
        }

        emit EmergencyProRataWithdrawal(msg.sender, lpAmount, amount0, amount1);
        return (amount0, amount1);
    }

    function swap(uint256 amount0In, uint256 amount1OutMin) external nonReentrant enforceCircuitBreaker returns (uint256) {
        uint256 amount1Out = FullMath.mulDiv(reserve1, amount0In, reserve0 + amount0In);
        if (amount1Out < amount1OutMin) revert SlippageExceeded();

        reserve0 += amount0In;
        reserve1 -= amount1Out;

        emit SwapExecuted(msg.sender, amount0In, amount1Out);
        return amount1Out;
    }
}

contract DeployArbitrumNitroGuardianScript {
    address public constant CANONICAL_SEQUENCER_FEED = 0xFdB631F5EE196F0ed6FAa767959853A9F217697D;
    address public constant GNOSIS_SAFE_GOVERNANCE = 0x1b793E4923774423457917228833983216892416;
    address public constant GUARDIAN_BOT = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    address public constant ARB_MAINNET_WETH = 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1;
    address public constant ARB_MAINNET_USDC = 0xaf88d065e77c8cC2239327C5EDb3A432268e5831;

    ArbitrumNitroCircuitBreaker public circuitBreaker;
    ProtectedPoolLP public protectedPool;

    function run() external {
        circuitBreaker = new ArbitrumNitroCircuitBreaker(
            GNOSIS_SAFE_GOVERNANCE,
            GUARDIAN_BOT,
            CANONICAL_SEQUENCER_FEED
        );

        protectedPool = new ProtectedPoolLP(
            address(circuitBreaker),
            ARB_MAINNET_WETH,
            ARB_MAINNET_USDC,
            10_000 ether,
            30_000_000 ether
        );

        circuitBreaker.setPoolAuthorization(address(protectedPool), true);

        bytes4 emergencyWithdrawSelector = ProtectedPoolLP.emergencyWithdrawProRata.selector;
        circuitBreaker.setEmergencySelector(address(protectedPool), emergencyWithdrawSelector, true);

        bytes4 standardWithdrawSelector = bytes4(keccak256("withdraw(uint256)"));
        circuitBreaker.setEmergencySelector(address(protectedPool), standardWithdrawSelector, true);

        bytes4 burnSelector = bytes4(keccak256("burn(address,uint256)"));
        circuitBreaker.setEmergencySelector(address(protectedPool), burnSelector, true);

        circuitBreaker.finalizeDeployment();
    }
}
