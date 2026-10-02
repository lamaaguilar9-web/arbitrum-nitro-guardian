# Arbitrum Nitro Guardian 🛡️⚡
**Autonomous Sub-45ms L2 Balance Sheet Invariant Sentinel & Circuit Breaker**  
*Exclusively Engineered for Arbitrum One (Nitro) Ecosystem: Camelot DEX & GMX v2*

[![Arbitrum One](https://img.shields.io/badge/Network-Arbitrum%20One%20Nitro-00a3ff.svg?logo=arbitrum)](https://arbitrum.io/)
[![Execution Model](https://img.shields.io/badge/Sequencer-FCFS%20Feed%20(No%20Mempool)-06b6d4.svg)](https://docs.arbitrum.io/)
[![Smart Contracts](https://img.shields.io/badge/Security-OpenZeppelin%20AccessControl-indigo.svg)](https://openzeppelin.com/)
[![Mitigation SLA](https://img.shields.io/badge/Mitigation%20SLA-Sub--45ms-10b981.svg)](#live-production-sentinel)
[![License](https://img.shields.io/badge/License-MIT%20%2F%20AS--IS-blue.svg)](./LEGAL.md)
[![Live Demo](https://img.shields.io/badge/Loom-Video%20Walkthrough-blueviolet.svg?logo=loom)](https://www.loom.com/share/9699ddd05d224ef980577a4ded396bfb)

---

### 🎥 Official Video Walkthrough & Live Architecture Demo
> **[Watch Demo: Arbitrum Nitro Guardián, seguridad no custodial (Loom Walkthrough)](https://www.loom.com/share/9699ddd05d224ef980577a4ded396bfb)**  
> *Demonstrating sub-45ms mitigation SLA, Camelot DEX Algebra AMM protection, GMX v2 collateral conservation, and non-custodial OpenZeppelin AccessControl governance.*

---

## 🏛️ Executive Summary & Institutional Purpose

**Arbitrum Nitro Guardian** is a high-frequency, autonomous Layer-2 circuit breaker purpose-built for the **Arbitrum One (Nitro)** ecosystem. Unlike Layer-1 networks with public mempools, Arbitrum Nitro processes transactions via a centralized sequencer following a strict **First-Come, First-Served (FCFS)** ordering model. 

When flash-loan arbitrageurs and adversarial MEV bots exploit price anomalies or extract unbacked collateral from Camelot DEX or GMX v2, mitigation cannot rely on passive mempool sniffing. It requires **sub-millisecond streaming telemetry directly from the Nitro sequencer feed, deterministic invariant evaluation, and ultra-low latency transaction dispatch** with dynamic EIP-1559 priority fee escalation.

---

## 🔬 Architectural Matrix: Solana vs. Ethereum vs. Arbitrum One

| Architectural Dimension | Solana Mainnet (`solana-guardian-agent`) | Ethereum Mainnet L1 (`evm-invariant-shield`) | Arbitrum One L2 (`arbitrum-nitro-guardian`) |
| :--- | :--- | :--- | :--- |
| **Ingestion Pipeline** | Yellowstone Geyser (gRPC slots) | WebSockets to dedicated nodes (`pendingTransactions`) | Direct WebSockets to Arbitrum Nitro Sequencer Feed |
| **Mempool Architecture** | Slot streaming (<45ms) | Public EVM mempool pre-block mining | **No public mempool; pure FCFS ordering** |
| **Mitigation Execution** | Jito MEV Bundles | Flashbots Protect / MEV-Share private relays | Direct ultra-low latency RPC connection to Sequencer |
| **Smart Contract Design** | Anchor Granular Account Pausable | OpenZeppelin `AccessControl` + `Pausable` | OpenZeppelin `AccessControl` (`PAUSER_ROLE`) |
| **Privilege Model** | Bot: Pause only; Unpause: Squads Multisig | Bot: `PAUSER_ROLE`; Unpause: Gnosis Safe | **Bot: `PAUSER_ROLE` only; Unpause: Gnosis Safe 3/5** |
| **Gas Pricing Model** | Solana Micro-lamport Priority Fees | Dynamic EIP-1559 base fee + priority tip | **Nitro Dual-Gas Model (L1 calldata + L2 computation)** |

---

## 🛡️ Asymmetric Role Segregation & Least Privilege Security

To protect monitored protocols against civil liability, false-positive DoS, and private key compromise:

1. **Principle of Least Privilege:**
   * The automated guardian bot wallet possesses **strictly the `PAUSER_ROLE`**.
   * The bot **CANNOT** unpause pools, transfer assets, upgrade contracts, or change governance parameters.
   * If the host server is compromised, the attacker cannot steal funds or brick protocols.
2. **Gnosis Safe Multisig Governance:**
   * The `UNPAUSER_ROLE` and `DEFAULT_ADMIN_ROLE` are exclusively assigned to a **Gnosis Safe (3/5 Multisig)** or DAO timelock.
   * Resumption of trading requires multi-signature human verification following post-incident forensics.
3. **Safety Timeout Safeguards:**
   * Granular, per-pool pauses with an automated `MAX_PAUSE_DURATION = 24 hours` fail-safe to prevent permanent fund lockups in the event of unforeseen market anomalies.

```
+-------------------------------------------------------------+
|                ARBITRUM ONE SECURITY BOUNDARY               |
+-------------------------------------------------------------+
|                                                             |
|   [ Nitro Sequencer Feed ] ---> Sub-5ms Invariant Engine    |
|                                         |                   |
|                                (Invariant Breach)           |
|                                         |                   |
|                                         v                   |
|                              [ Guardian Agent Bot ]         |
|                             (Holds PAUSER_ROLE Only)        |
|                                         |                   |
|                                (pausePool in <45ms)         |
|                                         v                   |
|                      [ ArbitrumNitroCircuitBreaker.sol ]     |
|                                         ^                   |
|                                         | (unpausePool)     |
|                                         |                   |
|                              [ Gnosis Safe Multisig ]       |
|                            (Holds UNPAUSER_ROLE & Admin)    |
|                                                             |
+-------------------------------------------------------------+
```

---

## ⚡ High-Availability RPC Redundancy & Failover Engine

Compliant with institutional standards, the Sentinel maintains an automated failover matrix:
* **Primary Gateway:** Arbitrum Nitro Dedicated Sequencer Endpoint (`https://arb1.arbitrum.io/rpc`).
* **Secondary Fallback:** High-Availability RPC Gateway (`https://arbitrum-one-rpc.publicnode.com`).
* **Failover SLA:** < 2ms automatic failover with active heartbeat detection upon HTTP 429/5xx or timeout > 500ms.

---

## 🚀 Dynamic EIP-1559 Gas Escalator

During high-threat exploitation events (`threat_score >= 0.82`), the Sentinel dynamically computes and increases `maxPriorityFeePerGas`:
$$	ext{PriorityFee}_{	ext{Emergency}} = 1.50 + (	ext{ThreatScore} 	imes 1.50) 	ext{ Gwei}$$
$$	ext{MaxFeePerGas} = (	ext{BaseFee} 	imes 2.5) + 	ext{PriorityFee}_{	ext{Emergency}}$$

This guarantees immediate sequencer inclusion ahead of adversarial batch reorganizations.

---

## 🧪 Testing Pipeline: Anvil (Foundry) Mainnet Forking

The project includes an automated test suite verifying state transitions over forked Arbitrum One mainnet state:

```bash
# Run Anvil Mainnet Fork Test Suite
python -m unittest tests/test_anvil_fork.py
```

**Verified Test Outputs:**
* `test_01_rpc_redundancy_and_failover`: Active endpoint failover verified in 0.002ms.
* `test_02_asymmetric_access_control`: Verifies bot can invoke `pausePool()`, while `unpausePool()` reverts with `Caller lacks UNPAUSER_ROLE`.
* `test_03_eip1559_gas_escalation`: Base 0.01 Gwei -> Priority 2.92 Gwei under exploit conditions.
* `test_04_end_to_end_mitigation_sla`: Full pipeline latency verified in **< 45ms**.

---

## ⚖️ Legal Specifications & Limitation of Liability

The software is governed by **[LEGAL.md](./LEGAL.md)**, incorporating mandatory institutional protections:

1. **[ESTADO ACTUAL - AS-IS]:** Software is provided "as-is" without warranty. No guarantee of mitigating 100% of exploits.
2. **[EXCLUSIÓN POR FALSOS POSITIVOS Y LATENCIA]:** Complete exclusion of civil and financial liability for false-positive pauses or network latency failures.
3. **[PRIVACIDAD Y DATOS PÚBLICOS]:** Exclusively processes public blockchain and Nitro sequencer data. Zero PII collection.

---

## 🖥️ Live Production Sentinel
 
* **Access Model:** Localhost Loopback / Secure SSH Tunnel (`http://127.0.0.1:5056`)
* **Tunnel Command:** `ssh -L 5056:127.0.0.1:5056 root@<HOST_IP>`
* **Dedicated Port:** `5056` (Confined to loopback per 7-Layer Security Matrix)
* **Architecture:** Standalone Python / FastAPI / Tailwind CSS / Web3
* **Repository:** [https://github.com/lamaaguilar9-web/arbitrum-nitro-guardian](https://github.com/lamaaguilar9-web/arbitrum-nitro-guardian)
