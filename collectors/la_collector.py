"""
LA (Lagrange) Collector
ZK proof marketplace.
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

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'la')
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

def collect_lagrange_data():
    """Collect Lagrange network data."""
    print("  [LAGRANGE] Fetching network data...")
    
    price_data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'lagrange',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'price': price_data.get('lagrange', {}) if price_data else {},
    }
    
    print(f"    LA price: ${result['price'].get('usd', 'N/A')}")
    
    return result

def collect_all():
    print(f"\n{'='*60}")
    print(f"LA (Lagrange) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = collect_lagrange_data()
    
    filepath = os.path.join(DATA_DIR, 'la_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
