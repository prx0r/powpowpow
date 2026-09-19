"""
Mining Metrics Collector for PowPowPow
Fetches hashrate, difficulty, miner revenue, and chain health metrics.
"""

import json
import os
import requests
from datetime import datetime

DATA_DIR = os.path.join(BASE_DIR, 'chains')
os.makedirs(DATA_DIR, exist_ok=True)

# Mining data sources (APIs or chain explorers)
MINING_SOURCES = {
    'XMR': {
        'type': 'randomx',
        'api': 'minero',
        'hashrate_url': 'https://minero.cc/api/network',
        'explorer': 'https://xmrchain.net',
    },
    'QUBIC': {
        'type': 'useful-pow',
        'api': 'qubic',
        'explorer': 'https://qubicscan.com',
    },
    'PRL': {
        'type': 'proof-of-useful-work',
        'api': 'pearl',
    },
    'NOCK': {
        'type': 'zk-pow',
        'api': 'nockchain',
    },
}

def fetch_monero_mining():
    """Fetch Monero mining metrics."""
    try:
        # Minero API
        resp = requests.get('https://minero.cc/api/network', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'hashrate': data.get('hashrate'),
                'difficulty': data.get('difficulty'),
                'block_reward': data.get('reward'),
                'block_time': data.get('block_time'),
                'blocks_per_day': 86400 / data.get('block_time', 120) if data.get('block_time') else 0,
                'mining_revenue_24h': data.get('mining_revenue_24h'),
                'pool_hashrate': data.get('pool_hashrate'),
            }
    except Exception as e:
        print(f"  Error: {e}")
    return None

def fetch_generic_mining(coin):
    """Fetch mining metrics from generic sources."""
    # Placeholder - would connect to specific chain APIs
    return {
        'hashrate': None,
        'difficulty': None,
        'block_reward': None,
        'block_time': None,
        'mining_revenue_24h': None,
        'pool_hashrate': None,
    }

def calculate_mining_derived(coin, mining_data, market_data=None):
    """Calculate derived mining metrics."""
    if not mining_data:
        return {}
    
    derived = {}
    
    # Block reward value
    if mining_data.get('block_reward') and market_data:
        price = market_data.get('last', 0)
        derived['block_reward_usd'] = mining_data['block_reward'] * price
    
    # Daily emission value
    if mining_data.get('block_reward') and mining_data.get('blocks_per_day'):
        daily_emission = mining_data['block_reward'] * mining_data['blocks_per_day']
        derived['daily_emission'] = daily_emission
        if market_data:
            derived['daily_emission_usd'] = daily_emission * market_data.get('last', 0)
    
    # Miner revenue to emission ratio
    if derived.get('daily_emission_usd') and mining_data.get('mining_revenue_24h'):
        derived['revenue_ratio'] = mining_data['mining_revenue_24h'] / derived['daily_emission_usd']
    
    return derived

def collect_mining_metrics():
    """Collect mining metrics for all tracked coins."""
    print(f"\n{'='*60}")
    print(f"Collecting Mining Metrics — {datetime.now()}")
    print(f"{'='*60}")
    
    all_metrics = {}
    
    for coin, source in MINING_SOURCES.items():
        print(f"\n[{coin}] ({source['type']})")
        
        if coin == 'XMR':
            mining_data = fetch_monero_mining()
        else:
            mining_data = fetch_generic_mining(coin)
        
        if mining_data:
            print(f"  Hashrate: {mining_data.get('hashrate', 'N/A')}")
            print(f"  Difficulty: {mining_data.get('difficulty', 'N/A')}")
            print(f"  Block Reward: {mining_data.get('block_reward', 'N/A')}")
            print(f"  Block Time: {mining_data.get('block_time', 'N/A')}")
            
            derived = calculate_mining_derived(coin, mining_data)
            mining_data['derived'] = derived
            
            if derived.get('daily_emission_usd'):
                print(f"  Daily Emission: ${derived['daily_emission_usd']:,.0f}")
        
        all_metrics[coin] = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'mining': mining_data,
        }
    
    # Save
    output_file = os.path.join(DATA_DIR, 'mining_metrics.json')
    with open(output_file, 'w') as f:
        json.dump(all_metrics, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    return all_metrics

if __name__ == '__main__':
    collect_mining_metrics()
