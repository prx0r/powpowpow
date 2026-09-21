"""
Historical Data Collector
Pulls from all available free APIs and data sources.
"""

import json
import os
import requests
import time
import csv
from datetime import datetime, timedelta
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'historical_data')
os.makedirs(DATA_DIR, exist_ok=True)

# Free data sources
SOURCES = {
    # Mining stats (free)
    'mining': {
        'kryptex_xmr': 'https://pool.kryptex.com/api/v1/coins/xmr/stats',
        'kryptex_prl': 'https://pool.kryptex.com/api/v1/coins/prl/stats',
        'minero_xmr': 'https://minero.cc/api/network',
    },
    # Exchange data (free)
    'exchange': {
        'coingecko_xmr': 'https://api.coingecko.com/api/v3/coins/monero/market_chart?vs_currency=usd&days=365',
        'coingecko_prl': 'https://api.coingecko.com/api/v3/coins/pearl/market_chart?vs_currency=usd&days=365',
        'coingecko_nock': 'https://api.coingecko.com/api/v3/coins/nockchain/market_chart?vs_currency=usd&days=365',
        'coingecko_xel': 'https://api.coingecko.com/api/v3/coins/xelis/market_chart?vs_currency=usd&days=365',
        'coingecko_xtm': 'https://api.coingecko.com/api/v3/coins/tari/market_chart?vs_currency=usd&days=365',
    },
    # Pool APIs (free)
    'pools': {
        'minexmr': 'https://minexmr.com/api/pool/stats',
        'pearlpool': 'https://pearlpool.cloud/api/v1/stats',
    },
    # Explorer APIs (free)
    'explorers': {
        'nockscan_blocks': 'https://nockscan.net/api/v1/recent-blocks',
        'nockscan_proof_rate': 'https://nockscan.net/api/v1/proof-rate',
    },
}

def fetch_json(url, params=None, timeout=10):
    """Fetch JSON from endpoint."""
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Error: {e}")
    return None

def collect_mining_data():
    """Collect mining stats from pools."""
    print("\n[MINING DATA]")
    
    mining_data = {}
    
    # XMR from Kryptex
    print("  Fetching XMR mining stats...")
    data = fetch_json(SOURCES['mining']['kryptex_xmr'])
    if data:
        mining_data['XMR'] = data
        print(f"    XMR: hashrate={data.get('networkHashrate')}, diff={data.get('difficulty')}")
    
    time.sleep(1)
    
    # XMR from Minero
    print("  Fetching XMR from Minero...")
    data = fetch_json(SOURCES['mining']['minero_xmr'])
    if data:
        if 'XMR' not in mining_data:
            mining_data['XMR'] = {}
        mining_data['XMR']['minero'] = data
        print(f"    XMR Minero: hashrate={data.get('hashrate')}")
    
    return mining_data

def collect_exchange_data():
    """Collect price/volume history from CoinGecko."""
    print("\n[EXCHANGE DATA]")
    
    exchange_data = {}
    
    for name, url in SOURCES['exchange'].items():
        print(f"  Fetching {name}...")
        data = fetch_json(url)
        if data:
            exchange_data[name] = data
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            print(f"    {name}: {len(prices)} price points, {len(volumes)} volume points")
        time.sleep(1.5)  # CoinGecko rate limit
    
    return exchange_data

def collect_pool_data():
    """Collect pool statistics."""
    print("\n[POOL DATA]")
    
    pool_data = {}
    
    for name, url in SOURCES['pools'].items():
        print(f"  Fetching {name}...")
        data = fetch_json(url)
        if data:
            pool_data[name] = data
            print(f"    {name}: {list(data.keys())[:5]}")
        time.sleep(1)
    
    return pool_data

def collect_explorer_data():
    """Collect from blockchain explorers."""
    print("\n[EXPLORER DATA]")
    
    explorer_data = {}
    
    for name, url in SOURCES['explorers'].items():
        print(f"  Fetching {name}...")
        data = fetch_json(url)
        if data:
            explorer_data[name] = data
            if isinstance(data, list):
                print(f"    {name}: {len(data)} records")
            elif isinstance(data, dict):
                print(f"    {name}: {list(data.keys())[:5]}")
        time.sleep(1)
    
    return explorer_data

def save_data(data, filename):
    """Save collected data."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n  Saved: {filepath}")

def collect_all():
    """Collect all historical data."""
    print(f"\n{'='*60}")
    print(f"Collecting Historical Data — {datetime.now()}")
    print(f"{'='*60}")
    
    all_data = {
        'collected_at': datetime.now().isoformat(),
        'mining': collect_mining_data(),
        'exchange': collect_exchange_data(),
        'pools': collect_pool_data(),
        'explorers': collect_explorer_data(),
    }
    
    # Save
    save_data(all_data, 'all_historical_data.json')
    
    # Summary
    print(f"\n{'='*60}")
    print("Collection Summary")
    print(f"{'='*60}")
    print(f"  Mining sources: {len(all_data['mining'])}")
    print(f"  Exchange sources: {len(all_data['exchange'])}")
    print(f"  Pool sources: {len(all_data['pools'])}")
    print(f"  Explorer sources: {len(all_data['explorers'])}")
    
    return all_data

if __name__ == '__main__':
    collect_all()
