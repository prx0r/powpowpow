"""
FLUX Collector
Compute nodes + PoW.
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

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'flux')
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

def collect_fluxnodes():
    """Collect Flux node data."""
    print("  [NODES] Fetching Flux nodes...")
    
    data = fetch_json('https://api.runonflux.io/daemon/getfluxnodecount')
    if data:
        print(f"    Node count: {data}")
        return data
    
    return None

def collect_benchmarks():
    """Collect Flux benchmarks."""
    print("  [BENCHMARKS] Fetching benchmarks...")
    
    data = fetch_json('https://api.runonflux.io/benchmark/getbenchmarks')
    if data:
        print(f"    Benchmarks: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_price():
    """Collect FLUX price."""
    print("  [PRICE] Fetching FLUX price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'flux',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'flux' in data:
        flux = data['flux']
        print(f"    FLUX: ${flux.get('usd', 'N/A')}")
        return flux
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"FLUX Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'nodes': collect_fluxnodes(),
        'benchmarks': collect_benchmarks(),
        'price': collect_price(),
    }
    
    filepath = os.path.join(DATA_DIR, 'flux_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
