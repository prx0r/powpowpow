"""
KAS (Kaspa) Collector
High-throughput PoW control.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from warehouse import store_raw_event

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'kas')
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
    """Collect KAS price."""
    print("  [PRICE] Fetching KAS price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'kaspa',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'kaspa' in data:
        kas = data['kaspa']
        print(f"    KAS: ${kas.get('usd', 'N/A')}")
        return kas
    
    return None

def collect_network():
    """Collect Kaspa network stats."""
    print("  [NETWORK] Fetching network stats...")
    
    data = fetch_json('https://api.kas.fyi/nodes')
    if data:
        print(f"    Nodes: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"KAS Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'price': collect_price(),
        'network': collect_network(),
    }
    
    filepath = os.path.join(DATA_DIR, 'kas_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
