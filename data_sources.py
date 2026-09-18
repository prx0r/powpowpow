"""
PowPowPow — Universal Data Sources Registry
Every chain, every data source, normalized.
"""

DATA_SOURCES = {
    'QUBIC': {
        'explorers': [
            {'name': 'Official Explorer', 'url': 'https://explorer.qubic.org', 'type': 'web'},
            {'name': 'QLI Network Stats', 'url': 'https://app.qubic.li', 'type': 'web'},
            {'name': 'QLI Analytics', 'url': 'https://analytics.qubic.li', 'type': 'web'},
        ],
        'apis': [
            {'name': 'Qubic RPC', 'url': 'https://rpc.qubic.org/v1', 'type': 'rpc', 'auth': False},
            {'name': 'DOGE Stats', 'url': 'https://doge-stats.qubic.org', 'type': 'rest', 'auth': False},
        ],
        'pools': [
            {'name': 'QLI Pool', 'url': 'https://pool.qubic.li'},
        ],
        'mining_software': ['Qubic Qiner', 'Qubic CPU Miner'],
        'community': {
            'discord': 'https://discord.gg/qubic',
            'twitter': '@QubicNetwork',
            'github': 'https://github.com/qubic',
        },
    },
    'PRL': {
        'explorers': [
            {'name': 'PRLScan', 'url': 'https://prlscan.com', 'type': 'web', 'has_stats': True},
            {'name': 'PearlTrack', 'url': 'https://pearltrack.io', 'type': 'web', 'has_stats': True},
        ],
        'apis': [
            {'name': 'PRLScan API', 'url': 'https://prlscan.com/api', 'type': 'rest', 'auth': False},
        ],
        'pools': [
            {'name': 'Kryptex', 'url': 'https://pool.kryptex.com/prl', 'hashrate': '21.9 EH/s'},
            {'name': 'PearlPool', 'url': 'https://pearlpool.cloud', 'type': 'pplns'},
            {'name': 'PearlPool.io', 'url': 'https://pearlpool.io', 'type': 'pplns'},
            {'name': 'Hero Miners', 'url': 'https://herominers.com/prl'},
            {'name': 'LuckyPool', 'url': 'https://luckypool.io/prl'},
        ],
        'mining_software': ['LolMiner', 'BZMiner', 'SRBMiner', 'vLLM Miner'],
        'community': {
            'discord': 'https://discord.gg/pearl',
            'twitter': '@PearlResearch',
            'github': 'https://github.com/pearl-research-labs',
        },
    },
    'NOCK': {
        'explorers': [
            {'name': 'NockBlocks', 'url': 'https://nockblocks.com', 'type': 'web', 'has_api': True},
            {'name': 'NockScan', 'url': 'https://nockscan.net', 'type': 'web', 'has_api': True},
        ],
        'apis': [
            {'name': 'NockBlocks API', 'url': 'https://nockblocks.com/api', 'type': 'rest', 'auth': False},
            {'name': 'NockScan API', 'url': 'https://nockscan.net/api/v1', 'type': 'rest', 'auth': False},
        ],
        'pools': [],
        'mining_software': ['Nockchain Miner'],
        'community': {
            'discord': 'https://discord.gg/nockchain',
            'twitter': '@Nockchain',
            'github': 'https://github.com/nockchain',
        },
    },
    'XMR': {
        'explorers': [
            {'name': 'XMRChain', 'url': 'https://xmrchain.net', 'type': 'web'},
            {'name': 'P2Pool Observer', 'url': 'https://p2pool.observer', 'type': 'web'},
        ],
        'apis': [
            {'name': 'Minero API', 'url': 'https://minero.cc/api', 'type': 'rest', 'auth': False},
            {'name': 'CoinWarz', 'url': 'https://api.coinwarz.com/v1/metrics?coin=xmr', 'type': 'rest', 'auth': True},
        ],
        'pools': [
            {'name': 'P2Pool', 'url': 'https://p2pool.io', 'type': 'p2pool'},
            {'name': 'SupportXMR', 'url': 'https://supportxmr.com'},
            {'name': 'MineXMR', 'url': 'https://minexmr.com'},
            {'name': 'Kryptex', 'url': 'https://pool.kryptex.com/xmr'},
        ],
        'mining_software': ['XMRig', 'SRBMiner', 'CPUMine'],
        'community': {
            'reddit': 'r/Monero',
            'github': 'https://github.com/monero-project',
        },
    },
    'GNK': {
        'explorers': [
            {'name': 'Gonka.gg', 'url': 'https://gonka.gg', 'type': 'web', 'has_api': True},
            {'name': 'GonkaLab', 'url': 'https://gonkalab.ai', 'type': 'web'},
            {'name': 'GNKScan', 'url': 'https://gnkscan.com', 'type': 'web'},
        ],
        'apis': [
            {'name': 'Gonka RPC', 'url': 'https://rpc.gonka.gg', 'type': 'rest', 'auth': False},
            {'name': 'Gonka Proxy', 'url': 'https://proxy.gonka.gg', 'type': 'openai', 'auth': True},
            {'name': 'OpenBroker', 'url': 'https://openbroker.gonka.gg', 'type': 'rest', 'auth': True},
        ],
        'pools': [],
        'mining_software': ['Gonka ML Node', 'vLLM Integration'],
        'community': {
            'discord': 'https://discord.gg/gonka',
            'twitter': '@gonka_gg',
            'github': 'https://github.com/gonka-ai',
        },
    },
    'TSC': {
        'explorers': [],
        'apis': [
            {'name': 'TensorCash Git', 'url': 'https://git.tensorcash.org', 'type': 'git'},
        ],
        'pools': [],
        'mining_software': ['TensorCash Miner', 'vLLM Fork', 'llama.cpp Fork'],
        'community': {
            'github': 'https://github.com/tensorcash',
        },
    },
    'XEL': {
        'explorers': [
            {'name': 'Xelis Explorer', 'url': 'https://explorer.xelis.io', 'type': 'web'},
            {'name': 'Xelis Stats', 'url': 'https://stats.xelis.io', 'type': 'web', 'has_stats': True},
        ],
        'apis': [
            {'name': 'Xelis Daemon', 'url': 'http://127.0.0.1:8080', 'type': 'rpc', 'auth': False},
        ],
        'pools': [
            {'name': 'Cedric Pool', 'url': 'https://xelis.cedric-crispin.com'},
            {'name': 'Kryptex', 'url': 'https://pool.kryptex.com/xel'},
        ],
        'mining_software': ['Xelis Miner', 'BZMiner', 'LolMiner'],
        'community': {
            'discord': 'https://discord.gg/xelis',
            'github': 'https://github.com/xelis-project',
        },
    },
    'XTM': {
        'explorers': [
            {'name': 'Tari Explorer', 'url': 'https://explore.tari.com', 'type': 'web'},
        ],
        'apis': [
            {'name': 'Tari gRPC', 'url': 'http://127.0.0.1:18142', 'type': 'grpc', 'auth': False},
        ],
        'pools': [
            {'name': 'Kryptex', 'url': 'https://pool.kryptex.com/xtm-rx', 'hashrate': '42.46 MH/s'},
            {'name': 'Merge Mining (XMR)', 'url': 'https://pool.kryptex.com/xmr'},
        ],
        'mining_software': ['XMRig', 'Tari Universe', 'Minotari'],
        'community': {
            'discord': 'https://discord.gg/tari',
            'github': 'https://github.com/tari-project',
        },
    },
    'NPT': {
        'explorers': [],
        'apis': [],
        'pools': [],
        'mining_software': [],
        'community': {},
    },
    'QTC': {
        'explorers': [
            {'name': 'QTC Explorer', 'url': 'https://explorer.superquantum.io', 'type': 'web'},
        ],
        'apis': [],
        'pools': [
            {'name': 'LuckyPool', 'url': 'https://luckypool.io/qtc', 'hashrate': '81.6%'},
            {'name': 'K1Pool', 'url': 'https://k1pool.com/qtc', 'hashrate': '13.2%'},
            {'name': 'QVerse', 'url': 'https://qverse.pro'},
        ],
        'mining_software': ['QTC Miner', 'cuQuantum'],
        'community': {
            'discord': 'https://discord.gg/qubitcoin',
        },
    },
}

def get_sources(coin):
    return DATA_SOURCES.get(coin.upper(), {})

def get_all_explorers():
    result = {}
    for coin, sources in DATA_SOURCES.items():
        result[coin] = sources.get('explorers', [])
    return result

def get_all_apis():
    result = {}
    for coin, sources in DATA_SOURCES.items():
        result[coin] = sources.get('apis', [])
    return result
