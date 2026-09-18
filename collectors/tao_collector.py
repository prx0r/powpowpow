"""
TAO (Bittensor) Collector
Intelligence/subnet markets.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/tao'
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

def collect_tao_data():
    """Collect Bittensor network data."""
    print("  [TAO] Fetching network data...")
    
    # CoinGecko price
    price_data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'bittensor',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    })
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'price': price_data.get('bittensor', {}) if price_data else {},
    }
    
    tao = result['price']
    print(f"    TAO: ${tao.get('usd', 'N/A')} ({tao.get('usd_24h_change', 0):.2f}%)")
    mcap = tao.get('usd_market_cap')
    if mcap:
        print(f"    Market Cap: ${mcap:,.0f}")
    
    return result

def collect_all():
    print(f"\n{'='*60}")
    print(f"TAO (Bittensor) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = collect_tao_data()
    
    filepath = os.path.join(DATA_DIR, 'tao_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
