"""
QRL (Quantum Resistant Ledger) Collector
Post-quantum PoW benchmark.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/qrl'
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_json(url, params=None, timeout=10):
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def collect_explorer_data():
    """Collect QRL explorer data."""
    print("  [EXPLORER] Fetching network stats...")
    
    # QRL Explorer API
    data = fetch_json('https://explorer.theqrl.org/api/network')
    if data:
        print(f"    Height: {data.get('height')}")
        print(f"    Hashrate: {data.get('hashrate')}")
        print(f"    Difficulty: {data.get('difficulty')}")
        print(f"    Reward: {data.get('reward')}")
        return data
    
    return None

def collect_market_data():
    """Collect QRL market data."""
    print("  [MARKET] Fetching market data...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'the-quantum-resistance-ledger',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    })
    
    if data and 'the-quantum-resistance-ledger' in data:
        qrl_data = data['the-quantum-resistance-ledger']
        print(f"    QRL: ${qrl_data.get('usd', 'N/A')}")
        print(f"    Market Cap: ${qrl_data.get('usd_market_cap', 'N/A'):,.0f}")
        return qrl_data
    
    return None

def collect_pool_data():
    """Collect mining pool data."""
    print("  [POOLS] Fetching pool data...")
    
    data = fetch_json('https://api.miningpoolstats.stream/v2/qrl')
    if data:
        pools = data.get('pools', [])
        print(f"    Pools: {len(pools)}")
        return data
    
    return None

def collect_all():
    """Collect all QRL data."""
    print(f"\n{'='*60}")
    print(f"QRL (Quantum Resistant Ledger) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'explorer': collect_explorer_data(),
        'market': collect_market_data(),
        'pools': collect_pool_data(),
    }
    
    # Save
    filepath = os.path.join(DATA_DIR, 'qrl_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
