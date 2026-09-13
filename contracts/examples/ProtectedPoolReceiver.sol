// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../IArbitrumNitroCircuitBreaker.sol";

/**
 * @title ProtectedPoolReceiver
 * @notice Example integration showing how a DEX pair (e.g. Camelot) or Lending Vault (e.g. GMX/Aave)
 * integrates with ArbitrumNitroCircuitBreaker with zero disruption to liquidations.
 */
contract ProtectedPoolReceiver {
    IArbitrumNitroCircuitBreaker public immutable circuitBreaker;

    modifier whenOperational() {
        require(circuitBreaker.isPoolOperational(address(this)), "ProtectedPool: POOL_EMERGENCY_PAUSED");
        _;
    }

    constructor(address _circuitBreaker) {
        circuitBreaker = IArbitrumNitroCircuitBreaker(_circuitBreaker);
    }

    // Swaps and new borrowings are blocked when paused
    function swap(uint256 amountIn, address recipient) external whenOperational returns (uint256 amountOut) {
        // Swap logic...
        return amountIn;
    }

    function borrow(uint256 amount) external whenOperational {
        // Borrow logic...
    }

    // Liquidations REMAIN ACTIVE to prevent bad debt accumulation,
    // relying strictly on external Chainlink price feeds.
    function liquidate(address borrower, uint256 debtToCover) external returns (uint256 collateralLiquidated) {
        // Liquidation logic remains accessible even if pool is paused...
        return debtToCover;
    }
}\n