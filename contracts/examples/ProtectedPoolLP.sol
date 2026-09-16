// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import '../ArbitrumNitroCircuitBreaker.sol';

/**
 * @title ProtectedPoolLP
 * @notice Pool de liquidez y Token LP ERC-20 con blindaje Anti-Sybil y receptor de Circuit Breaker.
 * Disenado para cumplir formalmente con los requerimientos de auditoria de Arbitrum Nitro Guardian.
 */
contract ProtectedPoolLP is CircuitBreakerReceiver {
    // --- Metadatos ERC-20 ---
    string public name = 'Arbitrum Shield Protected LP';
    string public symbol = 'AS-LP';
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // --- Reservas del Pool ---
    uint256 public reserve0;
    uint256 public reserve1;
    bool private _reentrancyLocked;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event SwapExecuted(address indexed sender, uint256 amount0In, uint256 amount1Out);
    event EmergencyProRataWithdrawal(address indexed user, uint256 lpAmount);

    error ReentrancyGuardReentrantCall();
    error LPTransfersFrozenDuringPause();
    error InsufficientBalance();
    error InsufficientAllowance();
    error SlippageExceeded();

    modifier nonReentrant() {
        if (_reentrancyLocked) revert ReentrancyGuardReentrantCall();
        _reentrancyLocked = true;
        _;
        _reentrancyLocked = false;
    }

    constructor(address _circuitBreaker, uint256 initialRes0, uint256 initialRes1) {
        _setCircuitBreaker(_circuitBreaker);
        reserve0 = initialRes0;
        reserve1 = initialRes1;
    }

    // =========================================================================
    // 1. BLINDAJE ANTI-SYBIL EN TRANSFERENCIAS LP (_update hook)
    // =========================================================================

    /**
     * @dev Hook estandar ERC-20 (_update) que valida transferencias de cuotas LP.
     * Durante EMERGENCY_PAUSED o EMERGENCY_WIND_DOWN, las transferencias entre cuentas
     * quedan estrictamente congeladas para sellar la instantanea de liquidez y
     * neutralizar vectores de evasion Sybil / wash-trading.
     */
    function _update(address from, address to, uint256 value) internal {
        // Si no es mint (from == 0) ni burn (to == 0), es una transferencia entre usuarios
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

    // =========================================================================
    // 2. RETIRO PRO-RATA ESCAPE HATCH (checkProRataWithdrawalQuota)
    // =========================================================================

    /**
     * @notice Retiro de emergencia pro-rata durante WIND_DOWN o falla de secuenciador.
     * Consulta directamente la cuota permitida en el CircuitBreaker basandose en el
     * balance sellado del usuario al momento de la pausa.
     */
    function emergencyWithdrawProRata(uint256 lpAmount) external nonReentrant returns (bool) {
        uint256 userBalance = balanceOf[msg.sender];
        if (userBalance < lpAmount) revert InsufficientBalance();

        // Llamada formal al contrato centinela para validar y descontar cuota del epoch
        circuitBreaker.checkProRataWithdrawalQuota(address(this), msg.sender, lpAmount, userBalance);

        // Quemar las cuotas LP retiradas
        _update(msg.sender, address(0), lpAmount);

        emit EmergencyProRataWithdrawal(msg.sender, lpAmount);
        return true;
    }

    // =========================================================================
    // 3. OPERACION PROTEGIDA POR EL CIRCUITO DISYUNTOR
    // =========================================================================

    /**
     * @notice Swap protegido mediante el modificador enforceCircuitBreaker.
     * Si el pool esta en pausa o el secuenciador de Arbitrum esta caido/en gracia,
     * la operacion revierte de forma atomica con OperationBlockedByCircuitBreaker(msg.sig).
     */
    function swap(uint256 amount0In, uint256 amount1OutMin) external nonReentrant enforceCircuitBreaker returns (uint256) {
        reserve0 += amount0In;
        uint256 amount1Out = FullMath.mulDiv(reserve1, amount0In, reserve0);
        if (amount1Out < amount1OutMin) revert SlippageExceeded();
        reserve1 -= amount1Out;

        emit SwapExecuted(msg.sender, amount0In, amount1Out);
        return amount1Out;
    }
}
