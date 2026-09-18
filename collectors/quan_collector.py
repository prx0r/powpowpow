"""
QUAN (Quantus) Collector
Post-quantum PoW with Prometheus metrics.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/quan'
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

def collect_price():
    """Collect QUAN price."""
    print("  [PRICE] Fetching QUAN price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'quantus',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'quantus' in data:
        quan = data['quantus']
        print(f"    QUAN: ${quan.get('usd', 'N/A')}")
        return quan
    
    return None

def collect_explorer():
    """Collect from Quantus explorer."""
    print("  [EXPLORER] Fetching chain data...")
    
    data = fetch_json('https://explorer.quantus.com/api/blocks?limit=10')
    if data:
        print(f"    Blocks: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"QUAN Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'price': collect_price(),
        'explorer': collect_explorer(),
    }
    
    filepath = os.path.join(DATA_DIR, 'quan_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
