"""
Extended Coin Collectors
Fetches data from external chains.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from warehouse import store_raw_event, store_normalized

DATA_DIR = os.path.join(BASE_DIR, 'historical_data', 'external')
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_json(url, params=None, timeout=10):
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        pass
    return None

def collect_coingecko_prices():
    """Collect prices for all coins from CoinGecko."""
    print("\n[COINGECKO] All coin prices...")
    
    # Map symbols to CoinGecko IDs
    cg_ids = {
        'TAO': 'bittensor',
        'KAS': 'kaspa',
        'QRL': 'the-quantum-resistance-ledger',
        'ZEPH': 'zephyr-protocol',
        'ALPH': 'alephium',
        'ERG': 'ergo',
        'XMR': 'monero',
        'QUBIC': 'qubic',
        'PRL': 'pearl',
        'NOCK': 'nockchain',
    }
    
    ids_str = ','.join(cg_ids.values())
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': ids_str,
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    }
    
    data = fetch_json(url, params)
    if data:
        # Map back to symbols
        prices = {}
        for symbol, cg_id in cg_ids.items():
            if cg_id in data:
                prices[symbol] = data[cg_id]
                print(f"  {symbol}: ${data[cg_id].get('usd', 'N/A')}")
        
        # Save
        filepath = os.path.join(DATA_DIR, 'prices.json')
        with open(filepath, 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'prices': prices}, f, indent=2)
        
        return prices
    return {}

def collect_kaspa_stats():
    """Collect Kaspa network stats."""
    print("\n[KAS] Network stats...")
    
    # Kaspa explorer API
    data = fetch_json('https://api.kas.fyi/nodes')
    if data:
        print(f"  Nodes: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    # Try alternative
    data = fetch_json('https://kaspa.org/api/stats')
    if data:
        print(f"  Stats: {list(data.keys())[:5]}")
        return data
    
    return None

def collect_qrl_stats():
    """Collect QRL network stats."""
    print("\n[QRL] Network stats...")
    
    data = fetch_json('https://explorer.theqrl.org/api/stats')
    if data:
        print(f"  Height: {data.get('height')}")
        print(f"  Difficulty: {data.get('difficulty')}")
        print(f"  Hashrate: {data.get('hashrate')}")
        return data
    
    return None

def collect_zeph_stats():
    """Collect Zephyr protocol stats."""
    print("\n[ZEPH] Network stats...")
    
    data = fetch_json('https://api.zephyrprotocol.com/v1/livestats')
    if data:
        print(f"  ZEPH price: ${data.get('zeph_usd')}")
        print(f"  Hashrate: {data.get('hashrate')}")
        return data
    
    return None

def collect_alph_stats():
    """Collect Alephium stats."""
    print("\n[ALPH] Network stats...")
    
    data = fetch_json('https://http://backend-1.alephium.info/infos')
    if data:
        print(f"  Height: {data.get('height')}")
        print(f"  Hashrate: {data.get('hashrate')}")
        return data
    
    return None

def collect_ergo_stats():
    """Collect Ergo stats."""
    print("\n[ERG] Network stats...")
    
    data = fetch_json('https://api.ergo.watch/infos/current')
    if data:
        print(f"  Height: {data.get('height')}")
        print(f"  Difficulty: {data.get('difficulty')}")
        return data
    
    return None

def collect_tao_subnet_info():
    """Collect Bittensor subnet info."""
    print("\n[TAO] Subnet info...")
    
    # Bittensor API
    data = fetch_json('https://api.bittensor.com/api/v1/subnets')
    if data:
        subnets = data.get('subnets', [])
        print(f"  Subnets: {len(subnets)}")
        return data
    
    return None

def collect_all():
    """Collect all external coin data."""
    print(f"\n{'='*60}")
    print(f"Collecting External Coin Data — {datetime.now()}")
    print(f"{'='*60}")
    
    all_data = {
        'collected_at': datetime.now().isoformat(),
        'prices': collect_coingecko_prices(),
        'kaspa': collect_kaspa_stats(),
        'qrl': collect_qrl_stats(),
        'zeph': collect_zeph_stats(),
        'alph': collect_alph_stats(),
        'ergo': collect_ergo_stats(),
        'tao': collect_tao_subnet_info(),
    }
    
    # Save
    filepath = os.path.join(DATA_DIR, 'external_data.json')
    with open(filepath, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return all_data

if __name__ == '__main__':
    collect_all()
