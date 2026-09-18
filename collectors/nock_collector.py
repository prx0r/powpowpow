"""
NOCK (Nockchain) Collector
ZK proof generation.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/nock'
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

def collect_nockscan():
    """Collect from NockScan API."""
    print("  [NOCKSCAN] Fetching block data...")
    
    blocks = fetch_json('https://nockscan.net/api/v1/recent-blocks')
    proof_rate = fetch_json('https://nockscan.net/api/v1/proof-rate')
    holders = fetch_json('https://nockscan.net/api/v1/holder-stats')
    
    result = {
        'blocks': blocks,
        'proof_rate': proof_rate,
        'holders': holders,
    }
    
    if blocks:
        print(f"    Blocks: {len(blocks.get('blocks', [])) if isinstance(blocks, dict) else 'N/A'}")
    if proof_rate:
        print(f"    Proof rate: {proof_rate.get('data', 'N/A')[:100] if isinstance(proof_rate, dict) else 'N/A'}")
    
    return result

def collect_price():
    """Collect NOCK price."""
    print("  [PRICE] Fetching NOCK price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'nockchain',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'nockchain' in data:
        nock = data['nockchain']
        print(f"    NOCK: ${nock.get('usd', 'N/A')}")
        return nock
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"NOCK Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'nockscan': collect_nockscan(),
        'price': collect_price(),
    }
    
    filepath = os.path.join(DATA_DIR, 'nock_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
