"""
THETA/TFUEL Collector
GPU EdgeCloud nodes.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/theta'
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
    """Collect THETA and TFUEL prices."""
    print("  [PRICE] Fetching THETA/TFUEL prices...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'theta-token,theta-fuel',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    result = {}
    if data:
        if 'theta-token' in data:
            result['THETA'] = data['theta-token']
            print(f"    THETA: ${data['theta-token'].get('usd', 'N/A')}")
        if 'theta-fuel' in data:
            result['TFUEL'] = data['theta-fuel']
            print(f"    TFUEL: ${data['theta-fuel'].get('usd', 'N/A')}")
    
    return result

def collect_edge_cloud():
    """Collect EdgeCloud network stats."""
    print("  [EDGECLOUD] Fetching network stats...")
    
    data = fetch_json('https://explorer.thetatoken.org/api/stats')
    if data:
        print(f"    Stats: {list(data.keys())[:5]}")
        return data
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"THETA Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'price': collect_price(),
        'edge_cloud': collect_edge_cloud(),
    }
    
    filepath = os.path.join(DATA_DIR, 'theta_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
