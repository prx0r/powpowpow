"""
TIG (The Innovation Game) Collector
Algorithmic efficiency / Optimisable PoW.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/tig'
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

def collect_tig_data():
    """Collect TIG network data."""
    print("  [TIG] Fetching network data...")
    
    price_data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'the-innovation-game',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    })
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'price': price_data.get('the-innovation-game', {}) if price_data else {},
    }
    
    tig = result['price']
    print(f"    TIG: ${tig.get('usd', 'N/A')} ({tig.get('usd_24h_change', 0):.2f}%)")
    mcap = tig.get('usd_market_cap')
    if mcap:
        print(f"    Market Cap: ${mcap:,.0f}")
    
    return result

def collect_algorithms():
    """Collect available algorithms from TIG API."""
    print("  [ALGORITHMS] Fetching algorithm list...")
    
    data = fetch_json('https://api.tig.foundation/v1/algorithms')
    if data:
        algos = data if isinstance(data, list) else data.get('algorithms', [])
        print(f"    Algorithms: {len(algos)}")
        return algos
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"TIG (The Innovation Game) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'market': collect_tig_data(),
        'algorithms': collect_algorithms(),
    }
    
    filepath = os.path.join(DATA_DIR, 'tig_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
