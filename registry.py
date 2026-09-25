import os
"""
PowPowPow research-universe registry (candidate pool, NOT runtime truth).

Runtime truth is v1_registry.get_v1() — 8 systems with verified
machine-readable supplier telemetry. Entries here graduate to V1 when
their telemetry is wired. Known warts: a QUAN2 duplicate key (old
double-listing, do not add more); prefer QUAN.
"""

REGISTRY = {
    # COMPUTE / USEFUL WORK
    'QUBIC': {
        'name': 'Qubic',
        'category': 'useful-work',
        'scarce_resource': 'CPU computation',
        'supplier_type': 'computor',
        'github': 'qubic/core',
        'api': 'https://rpc.qubic.org',
        'max_supply': 200_000_000_000_000,
    },
    'PRL': {
        'name': 'Pearl',
        'category': 'useful-work',
        'scarce_resource': 'H100 GPU matrix work',
        'supplier_type': 'miner',
        'github': 'pearl-research-labs/pearl',
        'rpc': 'pearld JSON-RPC',
        'max_supply': 2_100_000_000,
    },
    'NOCK': {
        'name': 'Nockchain',
        'category': 'useful-work',
        'scarce_resource': 'ZK proof generation',
        'supplier_type': 'prover',
        'github': 'nockchain/nockchain',
        'api': 'nockscan.net/api/v1',
        'max_supply': 4_294_967_296,
    },
    'QUAN': {
        'name': 'Quantus',
        'category': 'useful-work',
        'scarce_resource': 'Post-quantum PoW',
        'supplier_type': 'miner',
        'github': 'Quantus-Network/chain',
        'api': 'Prometheus :9900',
        'max_supply': 21_000_000,
    },
    'TSC': {
        'name': 'TensorCash',
        'category': 'useful-work',
        'scarce_resource': 'Verified AI inference',
        'supplier_type': 'miner',
        'github': 'tensorcash/tensorcash',
        'api': 'tensorcash.org/docs/rpc',
    },
    'GNK': {
        'name': 'Gonka',
        'category': 'useful-work',
        'scarce_resource': 'AI inference capacity',
        'supplier_type': 'host',
        'github': 'gonka-ai/gonka',
        'api': 'gonka.ai/docs/host/network-node-api',
    },
    'TIG': {
        'name': 'The Innovation Game',
        'category': 'useful-work',
        'scarce_resource': 'Algorithmic efficiency',
        'supplier_type': 'benchmarker',
        'github': 'tig-foundation',
        'api': 'swagger.tig.foundation',
    },
    'TAO': {
        'name': 'Bittensor',
        'category': 'intelligence',
        'scarce_resource': 'Machine intelligence',
        'supplier_type': 'miner/validator',
        'github': 'opentensor/bittensor',
        'api': 'metagraph query',
        'max_supply': 21_000_000,
    },

    # RESOURCE MARKETS
    'AKT': {
        'name': 'Akash',
        'category': 'resource-market',
        'scarce_resource': 'GPU/CPU capacity',
        'supplier_type': 'provider',
        'github': 'akash-network/node',
        'api': 'akash.network/docs/api-documentation/rest-api',
        'max_supply': 388_539_008,
    },
    'CLORE': {
        'name': 'Clore',
        'category': 'resource-market',
        'scarce_resource': 'GPU marketplace',
        'supplier_type': 'provider',
        'api': 'clore.ai/api-docs',
        'gigaspot': 'gigaspot-api-docs.clore.ai',
    },
    'NOS': {
        'name': 'Nosana',
        'category': 'resource-market',
        'scarce_resource': 'GPU compute',
        'supplier_type': 'host',
        'api': 'learn.nosana.com/api',
    },
    'TFUEL': {
        'name': 'Theta/TFUEL',
        'category': 'resource-market',
        'scarce_resource': 'GPU jobs + inference',
        'supplier_type': 'edge node',
        'api': 'docs.thetatoken.org/docs/theta-edgecloud-client-rpc-apis',
    },
    'FLUX': {
        'name': 'Flux',
        'category': 'resource-market',
        'scarce_resource': 'Compute nodes + PoW',
        'supplier_type': 'node',
        'github': 'RunOnFlux/flux',
        'api': 'docs.runonflux.io/fluxapi',
        'production': 'api.runonflux.io',
    },

    # POW / PRIVACY / SECURITY
    'XMR': {
        'name': 'Monero',
        'category': 'pow-privacy',
        'scarce_resource': 'CPU mining security',
        'supplier_type': 'miner',
        'github': 'monero-project/monero',
        'rpc': 'docs.getmonero.org/rpc-library/monerod-rpc',
    },
    'QUAN2': {
        'name': 'Quantus',
        'category': 'pow-privacy',
        'scarce_resource': 'Post-quantum PoW',
        'supplier_type': 'miner',
        'github': 'Quantus-Network/chain',
    },
    'QRL': {
        'name': 'QRL',
        'category': 'pow-privacy',
        'scarce_resource': 'XMSS signatures',
        'supplier_type': 'miner',
        'github': 'theQRL/QRL',
        'api': 'docs.theqrl.org/api/explorer-api',
        'max_supply': 105_000_000,
    },
    'MCM': {
        'name': 'Mochimo',
        'category': 'pow-privacy',
        'scarce_resource': 'WOTS+ GPU PoW',
        'supplier_type': 'miner',
        'github': 'mochimo-tech/mochimo',
        'max_supply': 76_500_000,
    },

    # CONTROL
    'KAS': {
        'name': 'Kaspa',
        'category': 'control',
        'scarce_resource': 'High-throughput PoW',
        'supplier_type': 'miner',
        'github': 'kaspanet/rusty-kaspa',
        'max_supply': 26_280_000_000,
    },
}

def get_registry():
    return REGISTRY

def get_coin(symbol):
    return REGISTRY.get(symbol.upper())

def get_all_symbols():
    return list(REGISTRY.keys())

def get_by_category(category):
    return {k: v for k, v in REGISTRY.items() if v.get('category') == category}
