"""
NOS (Nosana) Collector
GPU compute marketplace.
"""

import json
import os
import time
from datetime import datetime, timezone
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from core import fetch_json, store_normalized, utcnow

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'nos')
os.makedirs(DATA_DIR, exist_ok=True)


def collect_markets():
    """Collect Nosana GPU markets."""
    print("  [MARKETS] Fetching GPU markets...")
    
    data = fetch_json('https://api.nosana.io/markets', source_id='legacy', chain_id='venue')
    if data:
        print(f"    Markets: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_hosts():
    """Collect Nosana hosts."""
    print("  [HOSTS] Fetching host data...")
    
    data = fetch_json('https://api.nosana.io/hosts', source_id='legacy', chain_id='venue')
    if data:
        print(f"    Hosts: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_price():
    """Collect NOS price."""
    print("  [PRICE] Fetching NOS price...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'nosana',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    if data and 'nosana' in data:
        nos = data['nosana']
        print(f"    NOS: ${nos.get('usd', 'N/A')}")
        return nos
    
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"NOS (Nosana) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'markets': collect_markets(),
        'hosts': collect_hosts(),
        'price': collect_price(),
    }
    
    filepath = os.path.join(DATA_DIR, 'nos_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
