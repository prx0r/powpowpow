"""
XMR (Monero) Collector
CPU mining security benchmark.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/xmr'
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

def collect_localmonero():
    """Collect from LocalMonero API."""
    print("  [LOCALMONERO] Fetching XMR stats...")
    
    data = fetch_json('https://localmonero.co/blocks/api/get_stats')
    if data:
        print(f"    Height: {data.get('height')}")
        print(f"    Hashrate: {data.get('hashrate')}")
        print(f"    Difficulty: {data.get('difficulty')}")
        return data
    
    return None

def collect_price():
    """Collect XMR price."""
    print("  [PRICE] Fetching XMR price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'monero',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'monero' in data:
        xmr = data['monero']
        print(f"    XMR: ${xmr.get('usd', 'N/A')}")
        return xmr
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"XMR Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'localmonero': collect_localmonero(),
        'price': collect_price(),
    }
    
    filepath = os.path.join(DATA_DIR, 'xmr_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
