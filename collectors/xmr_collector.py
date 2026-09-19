"""
XMR (Monero) Collector — one-shot price/stats snapshot.

NOTE: chains/xmr/xmr_data.json output is legacy overwrite style,
superseded by collectors/chain_state.py normalized tables (fee_market,
mempool_snapshot, pool_snapshot, chain_snapshot). Kept for manual
spot-checks only.
"""

import json
import os
import time
from datetime import datetime, timezone
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from core import fetch_json, store_normalized, utcnow

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'xmr')
os.makedirs(DATA_DIR, exist_ok=True)


def collect_localmonero():
    """Collect from LocalMonero API."""
    print("  [LOCALMONERO] Fetching XMR stats...")
    
    data = fetch_json('https://localmonero.co/blocks/api/get_stats',
                      source_id='localmonero', chain_id='xmr')
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
    }, source_id='coingecko', chain_id='xmr')
    
    if data and 'monero' in data:
        xmr = data['monero']
        print(f"    XMR: ${xmr.get('usd', 'N/A')}")
        return xmr
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"XMR Collection — {utcnow()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': utcnow(),
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
