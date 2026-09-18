"""
CLORE Collector
GPU marketplace + mining.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/clore'
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

def collect_marketplace():
    """Collect Clore GPU marketplace data."""
    print("  [MARKETPLACE] Fetching GPU marketplace...")
    
    data = fetch_json('https://clore.ai/api/v1/marketplace')
    if data:
        servers = data if isinstance(data, list) else data.get('servers', [])
        print(f"    Servers: {len(servers)}")
        return servers
    
    return None

def collect_gigaspot():
    """Collect GigaSPOT bid/ask data."""
    print("  [GIGASPOT] Fetching bid/ask data...")
    
    data = fetch_json('https://gigaspot-api.clore.ai/v1/servers')
    if data:
        print(f"    Machines: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_price():
    """Collect CLORE price."""
    print("  [PRICE] Fetching CLORE price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'clore-ai',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'clore-ai' in data:
        clore = data['clore-ai']
        print(f"    CLORE: ${clore.get('usd', 'N/A')}")
        return clore
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"CLORE Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'marketplace': collect_marketplace(),
        'gigaspot': collect_gigaspot(),
        'price': collect_price(),
    }
    
    filepath = os.path.join(DATA_DIR, 'clore_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
