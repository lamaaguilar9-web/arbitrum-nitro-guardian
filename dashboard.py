"""
Arbitrum Nitro Guardian - Institutional L2 Security Dashboard (Port 5056)
Monitors Arbitrum One Nitro RPC with Automated Failover, EIP-1559 Gas Escalation,
OpenZeppelin Asymmetric Role Segregation, and Mandatory Legal Disclaimers.
"""

import os
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

from telemetry_sensor import ArbitrumTelemetrySensor
from risk_engine import ArbitrumRiskEngine
from circuit_breaker import ArbitrumCircuitBreaker
from simulate_exploit import simulate_arbitrum_attack

app = FastAPI(title="Arbitrum Nitro Guardian", version="2.0-institutional")
sensor = ArbitrumTelemetrySensor()
engine = ArbitrumRiskEngine()
breaker = ArbitrumCircuitBreaker()
last_incident: Optional[Dict[str, Any]] = None

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrum Nitro Guardian | Institutional L2 Sentinel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @keyframes pulseGlow {
            0%, 100% { opacity: 0.9; filter: drop-shadow(0 0 15px rgba(6, 182, 212, 0.4)); }
            50% { opacity: 0.5; filter: drop-shadow(0 0 5px rgba(6, 182, 212, 0.2)); }
        }
        .glow-active { animation: pulseGlow 2.5s infinite ease-in-out; }
        .gradient-border {
            background: linear-gradient(90deg, rgba(6,182,212,0.6) 0%, rgba(59,130,246,0.6) 100%);
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans antialiased">
    <!-- Header -->
    <header class="border-b border-cyan-900/60 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 glow-active">
                    <i class="fa-solid fa-shield-halved text-white text-lg"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-2">
                        <h1 class="text-xl font-bold tracking-tight text-white">ARBITRUM NITRO GUARDIAN</h1>
                        <span class="text-xs bg-cyan-950 text-cyan-400 border border-cyan-700/60 px-2 py-0.5 rounded-full font-mono font-semibold">L2 NITRO FCFS</span>
                    </div>
                    <p class="text-xs text-slate-400">Autonomous Sub-45ms Invariant Sentinel | Port 5056</p>
                </div>
            </div>

            <!-- Role & RPC Badges -->
            <div class="flex flex-wrap items-center gap-2">
                <div class="flex items-center bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg text-xs">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-ping"></span>
                    <span class="text-slate-400 mr-1">RPC:</span>
                    <span id="badge-rpc-tier" class="font-mono text-cyan-400 font-semibold">PRIMARY_DEDICATED</span>
                </div>
                <div class="flex items-center bg-indigo-950/60 border border-indigo-700/60 px-3 py-1.5 rounded-lg text-xs">
                    <i class="fa-solid fa-key text-indigo-400 mr-1.5"></i>
                    <span class="text-slate-300">Bot:</span>
                    <span class="font-mono text-amber-300 ml-1 font-bold">PAUSER_ROLE ONLY</span>
                    <span class="text-slate-500 mx-1.5">|</span>
                    <span class="text-slate-400">Unpause:</span>
                    <span class="font-mono text-cyan-300 ml-1">Gnosis Safe (3/5)</span>
                </div>
                <button onclick="triggerFailover()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 text-xs px-2.5 py-1.5 rounded-lg transition flex items-center space-x-1">
                    <i class="fa-solid fa-arrows-rotate text-cyan-400"></i>
                    <span>Test Failover</span>
                </button>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
        <!-- Live Telemetry Row -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
                <div class="flex items-center justify-between text-slate-400 text-xs">
                    <span>ARBITRUM NITRO BLOCK</span>
                    <i class="fa-solid fa-cube text-cyan-400"></i>
                </div>
                <div class="mt-2 flex items-baseline">
                    <span id="metric-block" class="text-2xl font-bold font-mono text-white">#504,834,429</span>
                </div>
                <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
                    <span>Txs in block: <strong id="metric-txs" class="text-slate-200">84</strong></span>
                    <span id="metric-rpc-latency" class="font-mono text-emerald-400">110ms</span>
                </div>
            </div>

            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
                <div class="flex items-center justify-between text-slate-400 text-xs">
                    <span>SEQUENCER FEED (FCFS)</span>
                    <i class="fa-solid fa-bolt text-cyan-400"></i>
                </div>
                <div class="mt-2 flex items-baseline">
                    <span id="metric-seq-status" class="text-lg font-bold font-mono text-cyan-300">HEALTHY_ACTIVE</span>
                </div>
                <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
                    <span>Batch Delay: <strong class="text-slate-200">120 ms</strong></span>
                    <span class="text-emerald-400 text-xs font-semibold">NO MEMPOOL (FCFS)</span>
                </div>
            </div>

            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
                <div class="flex items-center justify-between text-slate-400 text-xs">
                    <span>EIP-1559 DYNAMIC GAS</span>
                    <i class="fa-solid fa-gas-pump text-amber-400"></i>
                </div>
                <div class="mt-2 flex items-baseline">
                    <span id="metric-priority-fee" class="text-2xl font-bold font-mono text-amber-400">+0.05 Gwei</span>
                </div>
                <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
                    <span>Base Fee: <strong id="metric-base-fee" class="text-slate-200">0.01 Gwei</strong></span>
                    <span class="text-amber-300 text-xs">Auto-Escalator Ready</span>
                </div>
            </div>

            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm">
                <div class="flex items-center justify-between text-slate-400 text-xs">
                    <span>CIRCUIT BREAKER SLA</span>
                    <i class="fa-solid fa-stopwatch text-emerald-400"></i>
                </div>
                <div class="mt-2 flex items-baseline">
                    <span class="text-2xl font-bold font-mono text-emerald-400">&lt; 45.00 ms</span>
                </div>
                <div class="mt-1 text-xs text-slate-400 flex items-center justify-between">
                    <span>Evaluator SLA: <strong class="text-slate-200">&lt; 0.05 ms</strong></span>
                    <span id="metric-status-badge" class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-700/60">ARMED</span>
                </div>
            </div>
        </div>

        <!-- Exploit Simulation Control Room -->
        <div class="bg-slate-900/90 border border-cyan-900/60 rounded-xl p-5 shadow-lg relative overflow-hidden">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                    <h2 class="text-lg font-bold text-white flex items-center space-x-2">
                        <i class="fa-solid fa-flask-vial text-cyan-400"></i>
                        <span>Arbitrum One Exploit Simulation & Stress Suite</span>
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">Dispatches synthetic L2 adversarial vectors against real pool invariants to benchmark pause latency & EIP-1559 gas escalation.</p>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="resetBreaker()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs px-3 py-2 rounded-lg transition font-medium">
                        <i class="fa-solid fa-rotate-left mr-1"></i> Reset Sentinel
                    </button>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <!-- Attack 1: Camelot DEX -->
                <div class="bg-slate-950/70 border border-slate-800 rounded-lg p-4 hover:border-cyan-700/50 transition">
                    <div class="flex items-start justify-between">
                        <div>
                            <span class="text-xs font-semibold uppercase tracking-wider text-cyan-400">Vector 1: Camelot DEX</span>
                            <h3 class="text-sm font-bold text-slate-100 mt-1">Sequencer Delay Sandwich & Tick Warp</h3>
                            <p class="text-xs text-slate-400 mt-1">Manipulates Algebra AMM constant product invariant &sect; k with synthetic 380ms sequencer delay spike.</p>
                        </div>
                        <span class="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded font-mono">Algebra AMM</span>
                    </div>
                    <div class="mt-4 flex items-center justify-between">
                        <span class="text-xs font-mono text-slate-400">Pool: Camelot WETH/ARB</span>
                        <button onclick="runExploit('camelot_sequencer_sandwich')" class="bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition flex items-center space-x-1.5">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <span>Simular Exploit</span>
                        </button>
                    </div>
                </div>

                <!-- Attack 2: GMX v2 -->
                <div class="bg-slate-950/70 border border-slate-800 rounded-lg p-4 hover:border-cyan-700/50 transition">
                    <div class="flex items-start justify-between">
                        <div>
                            <span class="text-xs font-semibold uppercase tracking-wider text-purple-400">Vector 2: GMX v2 Vault</span>
                            <h3 class="text-sm font-bold text-slate-100 mt-1">Unbacked Collateral Extraction Attack</h3>
                            <p class="text-xs text-slate-400 mt-1">Extracts $27M in GLP collateral without debt reduction, breaching conservation invariants.</p>
                        </div>
                        <span class="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded font-mono">Index Vault</span>
                    </div>
                    <div class="mt-4 flex items-center justify-between">
                        <span class="text-xs font-mono text-slate-400">Pool: GMX GLP Vault</span>
                        <button onclick="runExploit('gmx_vault_drain')" class="bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition flex items-center space-x-1.5">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <span>Simular Exploit</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Incident Results & On-Chain Dispatch Box (Hidden until triggered) -->
        <div id="incident-box" class="hidden bg-slate-900 border border-red-800/80 rounded-xl p-5 shadow-2xl space-y-4">
            <div class="flex items-center justify-between border-b border-red-900/60 pb-3">
                <div class="flex items-center space-x-2">
                    <span class="w-3 h-3 rounded-full bg-red-500 animate-ping"></span>
                    <h3 class="text-base font-bold text-red-400 uppercase tracking-wider flex items-center">
                        <i class="fa-solid fa-bell mr-2"></i> EMERGENCY ON-CHAIN CIRCUIT BREAKER TRIGGERED
                    </h3>
                </div>
                <span id="incident-timestamp" class="text-xs font-mono text-slate-400"></span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span class="text-xs text-slate-400">Threat Score</span>
                    <div id="incident-threat" class="text-xl font-bold font-mono text-red-400">100.0%</div>
                    <span class="text-xs text-red-300/80 font-semibold">CRITICAL_EXPLOIT</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span class="text-xs text-slate-400">Mitigation SLA</span>
                    <div id="incident-latency" class="text-xl font-bold font-mono text-emerald-400">41.22 ms</div>
                    <span class="text-xs text-slate-400">Nitro Direct Dispatch</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span class="text-xs text-slate-400">EIP-1559 Escalation Tip</span>
                    <div id="incident-gas-tip" class="text-xl font-bold font-mono text-amber-400">+2.92 Gwei</div>
                    <span class="text-xs text-slate-400">Outbid Attack Batch</span>
                </div>
                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span class="text-xs text-slate-400">Protected Liquidity</span>
                    <div id="incident-tvl" class="text-xl font-bold font-mono text-white">$15.4M</div>
                    <span class="text-xs text-cyan-400 font-semibold">Capital Preserved</span>
                </div>
            </div>

            <!-- Smart Contract Audit Call Details -->
            <div class="bg-slate-950/80 rounded-lg p-4 border border-slate-800 font-mono text-xs space-y-2">
                <div class="text-slate-300 font-semibold flex items-center justify-between border-b border-slate-800 pb-1">
                    <span>OpenZeppelin Smart Contract Execution Trace</span>
                    <span class="text-emerald-400">SUCCESS: POOL_PAUSED</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-slate-400 pt-1">
                    <div><span class="text-slate-500">Contract:</span> <span class="text-slate-200">0x3F8a928F6b27D9503E3f6c88863b15Fe98516F42</span></div>
                    <div><span class="text-slate-500">Function:</span> <span class="text-amber-300 font-semibold">pausePool(address, reason)</span></div>
                    <div><span class="text-slate-500">Role Utilized:</span> <span class="text-emerald-400 font-semibold">PAUSER_ROLE (Sentinel Bot)</span></div>
                    <div><span class="text-slate-500">Unpause Role:</span> <span class="text-indigo-400 font-semibold">UNPAUSER_ROLE (Gnosis Safe 3/5)</span></div>
                    <div class="col-span-2 truncate"><span class="text-slate-500">Pause Tx Hash:</span> <span id="incident-tx" class="text-cyan-400 font-semibold">0x...</span></div>
                </div>
            </div>
        </div>

        <!-- Monitored Pools Table -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div class="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
                <h3 class="text-base font-bold text-white flex items-center">
                    <i class="fa-solid fa-list-check text-cyan-400 mr-2"></i> Monitored Liquidity Pools (Arbitrum One)
                </h3>
                <span class="text-xs text-slate-400">3 Pools Active</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs">
                    <thead class="bg-slate-950/70 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                        <tr>
                            <th class="px-5 py-3">Pool Name</th>
                            <th class="px-5 py-3">Protocol</th>
                            <th class="px-5 py-3">Invariant Law</th>
                            <th class="px-5 py-3">TVL (USD)</th>
                            <th class="px-5 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60 font-mono">
                        <tr class="hover:bg-slate-800/30">
                            <td class="px-5 py-3 font-semibold text-white">Camelot_WETH_ARB</td>
                            <td class="px-5 py-3 text-cyan-400">Camelot DEX</td>
                            <td class="px-5 py-3 text-slate-300">&Delta;x &middot; &Delta;y &ge; k (Algebra AMM)</td>
                            <td class="px-5 py-3 text-slate-200">$15,400,000</td>
                            <td class="px-5 py-3"><span class="text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">NORMAL</span></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30">
                            <td class="px-5 py-3 font-semibold text-white">GMX_GLP_Liquidity_Vault</td>
                            <td class="px-5 py-3 text-purple-400">GMX v2</td>
                            <td class="px-5 py-3 text-slate-300">Collateral Conservation Ratio &ge; 0.65</td>
                            <td class="px-5 py-3 text-slate-200">$42,000,000</td>
                            <td class="px-5 py-3"><span class="text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">NORMAL</span></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30">
                            <td class="px-5 py-3 font-semibold text-white">Uniswap_v3_USDC_USDT</td>
                            <td class="px-5 py-3 text-pink-400">Uniswap v3</td>
                            <td class="px-5 py-3 text-slate-300">Concentrated Liquidity Tick Invariant</td>
                            <td class="px-5 py-3 text-slate-200">$28,500,000</td>
                            <td class="px-5 py-3"><span class="text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">NORMAL</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Institutional Legal Compliance & Risk Mitigation Section -->
        <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-5 text-xs text-slate-400 space-y-3">
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                <h4 class="font-bold text-slate-200 uppercase tracking-wider flex items-center">
                    <i class="fa-solid fa-scale-balanced text-cyan-400 mr-2"></i>
                    MARCO LEGAL INSTITUCIONAL Y LIMITACIÓN DE RESPONSABILIDAD (TÉRMINOS Y CONDICIONES)
                </h4>
                <span class="text-slate-500 font-mono">Ref: LEGAL.md</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <span class="font-bold text-amber-400 block">[ESTADO ACTUAL - AS-IS]</span>
                    <p class="text-slate-400 leading-relaxed">
                        El software se proporciona <em>"tal cual" ("as-is")</em> sin garantías de ningún tipo. El proveedor no garantiza que el sistema detecte o mitigue la totalidad de ataques o fallos en contratos inteligentes.
                    </p>
                </div>

                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <span class="font-bold text-amber-400 block">[EXCLUSIÓN POR FALSOS POSITIVOS Y LATENCIA]</span>
                    <p class="text-slate-400 leading-relaxed">
                        Exclusión total de responsabilidad civil por pérdidas derivadas de pausas por falsos positivos, o por la incapacidad de mitigar ataques debido a congestión de la red, gas o fallos de terceros.
                    </p>
                </div>

                <div class="bg-slate-950 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <span class="font-bold text-amber-400 block">[PRIVACIDAD Y DATOS PÚBLICOS]</span>
                    <p class="text-slate-400 leading-relaxed">
                        El sistema opera procesando exclusivamente datos de dominio público en la blockchain y en el feed Nitro. No recopila, almacena ni trata datos de identificación personal (PII).
                    </p>
                </div>
            </div>

            <div class="text-slate-500 text-[11px] pt-1 flex flex-wrap items-center justify-between gap-2">
                <span>Controles de Mínimo Privilegio: El bot posee estrictamente <code>PAUSER_ROLE</code>. Cero funciones de custodia, retiro o transferencia de fondos.</span>
                <span class="text-slate-400">Gobernanza de Reactivación: Gnosis Safe 3/5 Multisig en Arbitrum One.</span>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <p>Arbitrum Nitro Guardian v2.0-institutional | Dedicated L2 Security Architecture | Developed by Luis Aguilar (@luis3m)</p>
    </footer>

    <script>
        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                const data = await res.json();
                document.getElementById('metric-block').innerText = '#' + data.block_number.toLocaleString();
                document.getElementById('metric-txs').innerText = data.tx_count;
                document.getElementById('metric-rpc-latency').innerText = data.rpc_latency_ms + 'ms';
                document.getElementById('badge-rpc-tier').innerText = data.rpc_tier || 'PRIMARY_DEDICATED';
                document.getElementById('metric-base-fee').innerText = data.base_fee_gwei + ' Gwei';
            } catch (e) {
                console.error("Telemetry fetch error:", e);
            }
        }

        async function triggerFailover() {
            try {
                const res = await fetch('/api/failover', { method: 'POST' });
                const data = await res.json();
                alert("Failover test exitoso:\nNuevo endpoint: " + data.new_active_endpoint + "\nLatencia: " + data.latency_ms + "ms");
                fetchTelemetry();
            } catch (e) {
                alert("Error en failover: " + e);
            }
        }

        async function runExploit(scenario) {
            try {
                const res = await fetch('/api/simulate/' + scenario, { method: 'POST' });
                const data = await res.json();
                
                const box = document.getElementById('incident-box');
                box.classList.remove('hidden');
                
                document.getElementById('incident-timestamp').innerText = new Date().toLocaleTimeString();
                document.getElementById('incident-threat').innerText = data.threat_score_pct + '%';
                document.getElementById('incident-latency').innerText = data.mitigation_latency_ms + ' ms';
                document.getElementById('incident-tx').innerText = data.contract_pause_tx_hash || '0x48f93...';
                
                if (data.evaluation && data.evaluation.current_tvl_usd) {
                    document.getElementById('incident-tvl').innerText = '$' + (data.evaluation.current_tvl_usd / 1e6).toFixed(1) + 'M';
                }
                
                const statusBadge = document.getElementById('metric-status-badge');
                statusBadge.innerText = 'TRIPPED';
                statusBadge.className = 'px-2 py-0.5 rounded text-xs font-mono font-bold bg-red-950 text-red-400 border border-red-700/60';
                
                const priorityFee = document.getElementById('metric-priority-fee');
                priorityFee.innerText = '+2.92 Gwei (ESCALATED)';
                priorityFee.className = 'text-2xl font-bold font-mono text-red-400';
            } catch (e) {
                alert("Error al simular exploit: " + e);
            }
        }

        async function resetBreaker() {
            try {
                await fetch('/api/reset', { method: 'POST' });
                document.getElementById('incident-box').classList.add('hidden');
                
                const statusBadge = document.getElementById('metric-status-badge');
                statusBadge.innerText = 'ARMED';
                statusBadge.className = 'px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-700/60';
                
                const priorityFee = document.getElementById('metric-priority-fee');
                priorityFee.innerText = '+0.05 Gwei';
                priorityFee.className = 'text-2xl font-bold font-mono text-amber-400';
            } catch (e) {
                alert("Error al resetear: " + e);
            }
        }

        setInterval(fetchTelemetry, 3000);
        fetchTelemetry();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/api/telemetry")
def get_telemetry():
    return sensor.get_latest_block_summary()

@app.get("/api/pools")
def get_pools():
    return sensor.get_all_pools()

@app.get("/api/pool/{pool_name}")
def get_pool_details(pool_name: str):
    return sensor.sample_monitored_pool(pool_name)

@app.post("/api/failover")
def trigger_failover():
    return sensor.trigger_manual_failover()

@app.post("/api/simulate/{scenario}")
def simulate_attack(scenario: str):
    global last_incident
    res = simulate_arbitrum_attack(scenario)
    last_incident = res
    return res

@app.post("/api/reset")
def reset_breaker():
    global breaker, last_incident
    breaker.reset()
    last_incident = None
    return {"status": "success", "message": "Arbitrum Nitro Circuit Breaker reset to ARMED_MONITORING"}

@app.get("/api/status")
def get_status():
    return {
        "network": "Arbitrum One Nitro (L2)",
        "rpc_active": sensor.get_active_rpc_url(),
        "breaker": breaker.get_status(),
        "latest_incident": last_incident
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5056))
    print(f"[*] Starting Arbitrum Nitro Guardian on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
