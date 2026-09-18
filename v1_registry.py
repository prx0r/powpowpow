"""
PowPowPow V1 Registry
8 systems with strict miner telemetry.
"""

V1_REGISTRY = {
    'PRL': {
        'name': 'Pearl',
        'physical_resource': 'H100/H200 GPU',
        'supplier_type': 'miner',
        'telemetry': 'Hashrate, pool flows, miner wallets',
        'marginal_cost': 'Power + hardware amortization',
        'reward': 'Mining revenue (PRL/day)',
        'supply_response': 'GPU entry/exit based on profitability',
        'price_source': 'SafeTrade L2',
        'github': 'pearl-research-labs/pearl',
        'rpc': 'pearld JSON-RPC',
        'explorer': 'prlscan.com',
        'pools': ['Kryptex', 'PearlPool', 'Hero Miners'],
        'hardware': ['H100', 'H200', 'RTX 4090', 'CMP 170HX'],
    },
    'QUBIC': {
        'name': 'Qubic',
        'physical_resource': 'CPU compute',
        'supplier_type': 'computor',
        'telemetry': 'Epochs, computors, ticks, contracts',
        'marginal_cost': 'Power + hardware amortization',
        'reward': 'Epoch rewards (QUBIC)',
        'supply_response': 'Computor changes per epoch',
        'price_source': 'SafeTrade L2',
        'github': 'qubic/core',
        'rpc': 'rpc.qubic.org',
        'explorer': 'explorer.qubic.org',
    },
    'QUAN': {
        'name': 'Quantus',
        'physical_resource': 'GPU/CPU',
        'supplier_type': 'miner',
        'telemetry': 'Prometheus metrics, hashrate, GPU efficiency',
        'marginal_cost': 'Power + hardware amortization',
        'reward': 'Block reward (QUAN)',
        'supply_response': 'Miner entry based on profitability',
        'price_source': 'SafeTrade L2',
        'github': 'Quantus-Network/chain',
        'prometheus': ':9900',
    },
    'XMR': {
        'name': 'Monero',
        'physical_resource': 'CPU',
        'supplier_type': 'miner',
        'telemetry': 'Hashrate, difficulty, mempool, emission',
        'marginal_cost': 'Power + CPU depreciation',
        'reward': 'Block reward (0.6 XMR tail)',
        'supply_response': 'CPU entry/exit',
        'price_source': 'CEX (Kraken, etc)',
        'github': 'monero-project/monero',
        'rpc': 'monerod RPC',
    },
    'KAS': {
        'name': 'Kaspa',
        'physical_resource': 'ASIC',
        'supplier_type': 'miner',
        'telemetry': 'Hashrate, difficulty, block time, rewards',
        'marginal_cost': 'Power + ASIC depreciation',
        'reward': 'Block reward (KAS)',
        'supply_response': 'ASIC entry/exit',
        'price_source': 'CEX',
        'github': 'kaspanet/rusty-kaspa',
        'block_rate': '10 blocks/sec',
    },
    'CLORE': {
        'name': 'Clore',
        'physical_resource': 'GPU marketplace',
        'supplier_type': 'provider',
        'telemetry': 'Machines, asks/bids, availability, utilization',
        'marginal_cost': 'Rental cost (opportunity cost)',
        'reward': 'Rental revenue (CLORE/USD)',
        'supply_response': 'Provider supply changes',
        'price_source': 'CEX',
        'api': 'clore.ai/api-docs',
        'gigaspot': 'GigaSPOT API',
    },
    'AKT': {
        'name': 'Akash',
        'physical_resource': 'GPU/CPU capacity',
        'supplier_type': 'provider',
        'telemetry': 'Provider inventory, GPU model/count, availability',
        'marginal_cost': 'Rental cost',
        'reward': 'Lease revenue (AKT)',
        'supply_response': 'Provider capacity changes',
        'price_source': 'CEX',
        'api': 'akash.network/docs/api-documentation',
    },
    'NOS': {
        'name': 'Nosana',
        'physical_resource': 'GPU compute',
        'supplier_type': 'host',
        'telemetry': 'Hosts, GPU markets, jobs, pricing, benchmarks',
        'marginal_cost': 'Rental cost',
        'reward': 'Job revenue (NOS)',
        'supply_response': 'Host supply changes',
        'price_source': 'CEX',
        'api': 'learn.nosana.com/api',
    },
}

def get_v1_registry():
    return V1_REGISTRY

def get_v1_coin(symbol):
    return V1_REGISTRY.get(symbol.upper())

def get_v1_symbols():
    return list(V1_REGISTRY.keys())
