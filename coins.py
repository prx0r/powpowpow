import os
"""
PowPowPow — Coin Registry
All tracked coins with GitHub repos, chain configs, and data sources.
"""

COINS = {
    'QUBIC': {
        'name': 'Qubic',
        'type': 'useful-compute',
        'consensus': 'useful-pow',
        'description': 'AI compute via brain-inspired mining',
        'github': {
            'org': 'qubic',
            'repos': ['core', 'go-qubic-nodes', 'qct', 'docs', 'oracle-machine', 'qubic-cli', 'core-lite'],
            'main': 'qubic/core',
            'stars': 185,
            'language': 'C++',
        },
        'market': {
            'safetrade': 'qubicusdt',
            'mexc': 'QUBIC/USDT',
            'bitget': 'QUBIC/USDT',
        },
        'chain': {
            'max_supply': 200_000_000_000,
            'emission_per_day': 1_728_000_000,
            'block_time': None,
            'consensus': 'useful-pow',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'PRL': {
        'name': 'Pearl',
        'type': 'useful-compute',
        'consensus': 'proof-of-useful-work',
        'description': 'L1 PoUW blockchain where mining is by-product of AI inference',
        'github': {
            'org': 'pearl-research-labs',
            'repos': ['pearl'],
            'main': 'pearl-research-labs/pearl',
            'stars': None,
            'language': 'Rust',
        },
        'market': {
            'safetrade': 'prlusdt',
            'mexc': 'PRL/USDT',
            'bitget': 'PRL/USDT',
        },
        'chain': {
            'max_supply': 2_100_000_000,
            'emission_per_day': 500_000,
            'block_time': 194,
            'consensus': 'proof-of-useful-work',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'NOCK': {
        'name': 'Nockchain',
        'type': 'zk-pow',
        'consensus': 'zk-proof-of-work',
        'description': 'ZK-PoW blockchain combining sound money with verifiable computation',
        'github': {
            'org': 'nockchain',
            'repos': ['nockchain'],
            'main': 'nockchain/nockchain',
            'stars': 491,
            'language': 'Rust',
        },
        'market': {
            'safetrade': 'nockusdt',
            'mexc': 'NOCK/USDT',
        },
        'chain': {
            'max_supply': 2**32,  # 4,294,967,296
            'emission_per_day': 50_000,
            'block_time': None,
            'consensus': 'zk-pow',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'XMR': {
        'name': 'Monero',
        'type': 'privacy',
        'consensus': 'randomx',
        'description': 'Secure, private, untraceable cryptocurrency',
        'github': {
            'org': 'monero-project',
            'repos': ['monero', 'monero-gui', 'research-lab'],
            'main': 'monero-project/monero',
            'stars': 10_839,
            'language': 'C++',
        },
        'market': {
            'safetrade': 'xmrusdt',
            'mexc': 'XMR/USDT',
        },
        'chain': {
            'max_supply': None,  # Tail emission
            'emission_per_day': 2_844,
            'block_time': 120,
            'consensus': 'randomx',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'GNK': {
        'name': 'Gonka',
        'type': 'compute-market',
        'consensus': 'proof-of-work-2',
        'description': 'Decentralized AI inference infrastructure',
        'github': {
            'org': 'gonka-ai',
            'repos': ['gonka', 'gonka-openai'],
            'main': 'gonka-ai/gonka',
            'stars': 621,
            'language': 'Go',
        },
        'market': {
            'safetrade': 'gnkusdt',
        },
        'chain': {
            'max_supply': None,
            'emission_per_day': None,
            'block_time': None,
            'consensus': 'proof-of-work-2',
        },
        'data_sources': ['safetrade_ws', 'github_api'],
    },
    'TSC': {
        'name': 'TensorCash',
        'type': 'ai-inference',
        'consensus': 'proof-of-inference',
        'description': 'Bitcoin-derived L1 where AI inference is mining work',
        'github': {
            'org': 'tensorcash',
            'repos': ['tensorcash', 'bcore', 'llama.cpp', 'vllm', 'gnark'],
            'main': 'tensorcash/tensorcash',
            'stars': None,
            'language': 'Python',
        },
        'market': {
            'safetrade': 'tscusdt',
        },
        'chain': {
            'max_supply': None,
            'emission_per_day': None,
            'block_time': None,
            'consensus': 'proof-of-inference',
        },
        'data_sources': ['safetrade_ws', 'github_api'],
    },
    'XEL': {
        'name': 'Xelis',
        'type': 'privacy-dag',
        'consensus': 'xelis-hash',
        'description': 'BlockDAG with homomorphic encryption and smart contracts',
        'github': {
            'org': 'xelis-project',
            'repos': ['xelis-blockchain', 'xelis-hash', 'xelis-vm', 'xelis-he'],
            'main': 'xelis-project/xelis-blockchain',
            'stars': 436,
            'language': 'Rust',
        },
        'market': {
            'safetrade': 'xelusdt',
            'mexc': 'XEL/USDT',
        },
        'chain': {
            'max_supply': 18_400_000,
            'emission_per_day': None,
            'block_time': 5,
            'consensus': 'xelis-hash',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'XTM': {
        'name': 'Tari',
        'type': 'privacy',
        'consensus': 'randomx',
        'description': 'Mimblewimble privacy with RandomX CPU mining',
        'github': {
            'org': 'tari-project',
            'repos': ['tari', 'tari-crypto', 'universe', 'rfcs'],
            'main': 'tari-project/tari',
            'stars': 495,
            'language': 'Rust',
        },
        'market': {
            'safetrade': 'xtmusdt',
            'mexc': 'XTM/USDT',
        },
        'chain': {
            'max_supply': 21_000_000_000,
            'emission_per_day': None,
            'block_time': 120,
            'consensus': 'randomx',
        },
        'data_sources': ['safetrade_ws', 'mexc_api', 'github_api'],
    },
    'NPT': {
        'name': 'Neptune Cash',
        'type': 'privacy-stark',
        'consensus': 'zk-stark',
        'description': 'Private-by-default STARK transactions with post-quantum crypto',
        'github': {
            'org': None,
            'repos': [],
            'main': None,
            'stars': None,
            'language': None,
        },
        'market': {
            'safetrade': 'nptusdt',
        },
        'chain': {
            'max_supply': None,
            'emission_per_day': None,
            'block_time': None,
            'consensus': 'zk-stark',
        },
        'data_sources': ['safetrade_ws'],
    },
    'QTC': {
        'name': 'Qubitcoin',
        'type': 'quantum-sim',
        'consensus': 'quantum-simulation',
        'description': 'PoW via quantum circuit simulation',
        'github': {
            'org': None,
            'repos': [],
            'main': None,
            'stars': None,
            'language': None,
        },
        'market': {
            'safetrade': 'qtcusdt',
        },
        'chain': {
            'max_supply': None,
            'emission_per_day': None,
            'block_time': None,
            'consensus': 'quantum-simulation',
        },
        'data_sources': ['safetrade_ws'],
    },
}

def get_coin(symbol):
    return COINS.get(symbol.upper())

def get_all_symbols():
    return list(COINS.keys())

def get_github_repos():
    """Get all GitHub repos to track."""
    repos = []
    for symbol, config in COINS.items():
        gh = config.get('github', {})
        if gh.get('main'):
            repos.append({
                'coin': symbol,
                'repo': gh['main'],
                'stars': gh.get('stars'),
                'language': gh.get('language'),
            })
    return repos
