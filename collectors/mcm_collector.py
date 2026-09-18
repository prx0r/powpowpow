"""
MCM (Mochimo) Collector
Post-quantum GPU PoW.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/mcm'
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

def collect_mcm_data():
    """Collect Mochimo network data."""
    print("  [MOCHIMO] Fetching network data...")
    
    price_data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'mochimo',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    })
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'price': price_data.get('mochimo', {}) if price_data else {},
    }
    
    mcm = result['price']
    if mcm:
        change = mcm.get('usd_24h_change')
        change_str = f"{change:.2f}%" if change is not None else "N/A"
        mcap = mcm.get('usd_market_cap')
        mcap_str = f"${mcap:,.0f}" if mcap else "N/A"
        print(f"    MCM: ${mcm.get('usd', 'N/A')} ({change_str})")
        print(f"    Market Cap: {mcap_str}")
    else:
        print(f"    MCM: No CoinGecko data (may need alternative source)")
    
    return result

def collect_all():
    print(f"\n{'='*60}")
    print(f"MCM (Mochimo) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'market': collect_mcm_data(),
    }
    
    filepath = os.path.join(DATA_DIR, 'mcm_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
