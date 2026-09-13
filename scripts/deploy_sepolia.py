"""
Arbitrum Nitro Guardian - Public Testnet Deployment Script (Arbitrum Sepolia)
Network: Arbitrum Sepolia (Chain ID: 421614)
RPC: https://sepolia-rollup.arbitrum.io/rpc
Sequencer Uptime Feed (Sepolia): 0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69
"""

import os
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DeploySepolia")

SEPOLIA_CONFIG = {
    "network_name": "Arbitrum Sepolia (L2 Testnet)",
    "chain_id": 421614,
    "rpc_url": "https://sepolia-rollup.arbitrum.io/rpc",
    "explorer": "https://sepolia.arbiscan.io",
    "chainlink_sequencer_feed": "0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69",
    "suggested_gnosis_safe_3_5": "0x1b793E4923774423457917228833983216892416",
    "guardian_bot_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
}

def generate_deployment_manifest() -> Dict[str, Any]:
    logger.info("[*] Generating Arbitrum Sepolia deployment manifest...")
    manifest = {
        "deployment_target": SEPOLIA_CONFIG["network_name"],
        "chain_id": SEPOLIA_CONFIG["chain_id"],
        "rpc_endpoint": SEPOLIA_CONFIG["rpc_url"],
        "constructor_arguments": {
            "_governanceSafe": SEPOLIA_CONFIG["suggested_gnosis_safe_3_5"],
            "_botAddress": SEPOLIA_CONFIG["guardian_bot_address"],
            "_sequencerFeed": SEPOLIA_CONFIG["chainlink_sequencer_feed"]
        },
        "grace_period_enforced_seconds": 3600,
        "max_consecutive_pauses": 2,
        "compiler": "solc 0.8.20 + EVM Paris/Shanghai",
        "gas_estimate_deployment_gwei": 0.10
    }
    
    with open("deployment_manifest_sepolia.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"[+] Deployment manifest written: deployment_manifest_sepolia.json")
    return manifest

if __name__ == "__main__":
    generate_deployment_manifest()
