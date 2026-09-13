// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FullMath
 * @notice Facilitates multiplication and division that can have overflow of an intermediate value without loss of precision.
 * @dev Handles "phantom overflow": i.e. allows multiplication and division where (a * b) > 2**256 - 1, but (a * b) / denominator fits in uint256.
 * Standard implementation from Uniswap v3 / PRBMath.
 */
library FullMath {
    function mulDiv(
        uint256 a,
        uint256 b,
        uint256 denominator
    ) internal pure returns (uint256 result) {
        unchecked {
            // 512-bit multiply [prod1 prod0] = a * b
            uint256 prod0; // Least significant 256 bits of the product
            uint256 prod1; // Most significant 256 bits of the product
            assembly {
                let mm := mulmod(a, b, not(0))
                prod0 := mul(a, b)
                prod1 := sub(sub(mm, prod0), lt(mm, prod0))
            }

            // Handle non-overflow cases, 256 by 256 division
            if (prod1 == 0) {
                require(denominator > 0, "FullMath: zero denominator");
                assembly {
                    result := div(prod0, denominator)
                }
                return result;
            }

            // Make sure the result is less than 2**256. Also prevents denominator == 0
            require(denominator > prod1, "FullMath: 512-bit overflow");

            // Remainder for division
            uint256 remainder;
            assembly {
                remainder := mulmod(a, b, denominator)
            }

            // Subtract 256 bit number from 512 bit number
            assembly {
                prod1 := sub(prod1, gt(remainder, prod0))
                prod0 := sub(prod0, remainder)
            }

            // Factor powers of two out of denominator
            // Compute largest power of two divisor of denominator. Always >= 1.
            uint256 twos = denominator & (~denominator + 1);
            assembly {
                denominator := div(denominator, twos)
                prod0 := div(prod0, twos)
                twos := add(div(sub(0, twos), twos), 1)
            }

            // Shift in bits from prod1 into prod0
            prod0 |= prod1 * twos;

            // Invert denominator mod 2**256
            // Now that denominator is an odd number, it has an inverse modulo 2**256
            uint256 inverse = (3 * denominator) ^ 2;
            inverse *= 2 - denominator * inverse; // inverse mod 2**8
            inverse *= 2 - denominator * inverse; // inverse mod 2**16
            inverse *= 2 - denominator * inverse; // inverse mod 2**32
            inverse *= 2 - denominator * inverse; // inverse mod 2**64
            inverse *= 2 - denominator * inverse; // inverse mod 2**128
            inverse *= 2 - denominator * inverse; // inverse mod 2**256

            // Because the division is now exact we can divide by multiplying
            // with the modular inverse of denominator!
            result = prod0 * inverse;
            return result;
        }
    }
}
