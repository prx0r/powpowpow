import os
"""
Extended Coin Registry
All tracked coins including external comparison set.
"""

COINS = {
    # SafeTrade Experimental Core
    'QUBIC': {
        'name': 'Qubic',
        'type': 'useful-compute',
        'consensus': 'Useful PoW',
        'venue': 'safetrade',
        'github': 'qubic/core',
        'max_supply': 200_000_000_000_000,
    },
    'PRL': {
        'name': 'Pearl',
        'type': 'useful-compute',
        'consensus': 'Proof-of-Useful-Work',
        'venue': 'safetrade',
        'github': 'pearl-research-labs/pearl',
        'max_supply': 2_100_000_000,
    },
    'NOCK': {
        'name': 'Nockchain',
        'type': 'zk-pow',
        'consensus': 'ZK-PoW',
        'venue': 'safetrade',
        'github': 'nockchain/nockchain',
        'max_supply': 4_294_967_296,
    },
    'QUAN': {
        'name': 'Quantus',
        'type': 'post-quantum',
        'consensus': 'Post-Quantum PoW',
        'venue': 'safetrade',
        'github': 'Quantus-Network/chain',
        'max_supply': 21_000_000,
    },
    'TSC': {
        'name': 'TensorCash',
        'type': 'ai-inference',
        'consensus': 'Proof-of-Inference',
        'venue': 'safetrade',
        'github': 'tensorcash/tensorcash',
    },
    'GNK': {
        'name': 'Gonka',
        'type': 'compute-market',
        'consensus': 'PoW 2.0',
        'venue': 'safetrade',
        'github': 'gonka-ai/gonka',
    },
    'XMR': {
        'name': 'Monero',
        'type': 'privacy',
        'consensus': 'RandomX',
        'venue': 'safetrade',
        'github': 'monero-project/monero',
        'max_supply': None,  # Tail emission
    },
    
    # External Comparison Set
    'TAO': {
        'name': 'Bittensor',
        'type': 'intelligence-market',
        'consensus': 'Proof of Intelligence',
        'venue': 'external',
        'github': 'opentensor/bittensor',
        'max_supply': 21_000_000,
        'subnets': True,
    },
    'KAS': {
        'name': 'Kaspa',
        'type': 'high-throughput',
        'consensus': 'PHANTOM/GHOSTDAG',
        'venue': 'external',
        'github': 'kaspanet/rusty-kaspa',
        'max_supply': 26_280_000_000,
        'blocks_per_second': 10,
    },
    'QRL': {
        'name': 'Quantum Resistant Ledger',
        'type': 'post-quantum',
        'consensus': 'RandomX + XMSS',
        'venue': 'external',
        'github': 'theQRL/QRL',
        'max_supply': 105_000_000,
    },
    'ZEPH': {
        'name': 'Zephyr Protocol',
        'type': 'monetary-reserve',
        'consensus': 'RandomX + Stablecoin',
        'venue': 'external',
        'github': 'ZephyrProtocol/Zephyr',
    },
    'ALPH': {
        'name': 'Alephium',
        'type': 'sharded',
        'consensus': 'Blockflow',
        'venue': 'external',
        'github': 'alephium/alephium',
        'max_supply': 8_500_000_000,
    },
    'ERG': {
        'name': 'Ergo',
        'type': 'utxo-defi',
        'consensus': 'Autolykos',
        'venue': 'external',
        'github': 'ergoplatform/ergo',
        'max_supply': 97_739_924,
    },
    'AKT': {
        'name': 'Akash',
        'type': 'compute-market',
        'consensus': 'Proof of Stake',
        'venue': 'external',
        'github': 'akash-network/node',
        'max_supply': 388_539_008,
        'resource': 'GPU/CPU capacity',
    },
    'PHA': {
        'name': 'Phala',
        'type': 'tee-compute',
        'consensus': 'TEE + PoS',
        'venue': 'external',
        'github': 'Phala-Network/phala-blockchain',
        'resource': 'attested confidential compute',
    },
    'LA': {
        'name': 'Lagrange',
        'type': 'zk-proving',
        'consensus': 'Proof Marketplace',
        'venue': 'external',
        'github': 'lagrange-labs/lagrange',
        'resource': 'ZK proof generation',
    },
    'TIG': {
        'name': 'The Innovation Game',
        'type': 'algorithmic-efficiency',
        'consensus': 'Optimisable Proof of Work',
        'venue': 'external',
        'github': 'tig-foundation',
        'resource': 'Algorithmic efficiency',
    },
    'MCM': {
        'name': 'Mochimo',
        'type': 'post-quantum-pow',
        'consensus': 'WOTS+ GPU PoW',
        'venue': 'external',
        'github': 'mochimo-tech/mochimo',
        'max_supply': 76_500_000,
        'resource': 'GPU proof generation',
    },
}

def get_coin(symbol):
    return COINS.get(symbol.upper())

def get_all_symbols():
    return list(COINS.keys())

def get_safetrade_coins():
    return {k: v for k, v in COINS.items() if v.get('venue') == 'safetrade'}

def get_external_coins():
    return {k: v for k, v in COINS.items() if v.get('venue') == 'external'}
