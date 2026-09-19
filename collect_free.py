"""
Free Data Sources Collector
Pulls from all free APIs without keys.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

DATA_DIR = os.path.join(BASE_DIR, 'historical_data')
os.makedirs(DATA_DIR, exist_ok=True)

# Free APIs (no key required)
FREE_APIS = {
    # OHLCV data
    'binance': {
        'base': 'https://api.binance.com/api/v3',
        'pairs': ['XMRUSDT', 'BTCUSDT', 'ETHUSDT'],
    },
    
    # Mining stats
    'localmonero': {
        'stats': 'https://localmonero.co/blocks/api/get_stats',
        'block': 'https://localmonero.co/blocks/api/get_block_header/',
    },
    
    # Pool stats
    'minexmr': {
        'stats': 'https://minexmr.com/api/pool/stats',
    },
    
    # CoinGecko (free tier)
    'coingecko': {
        'simple': 'https://api.coingecko.com/api/v3/simple/price',
        'market': 'https://api.coingecko.com/api/v3/coins/',
    },
    
    # CoinCap (free)
    'coincap': {
        'assets': 'https://api.coincap.io/v2/assets',
        'history': 'https://api.coincap.io/v2/assets/{id}/history',
    },
    
    # CryptoCompare (free)
    'cryptocompare': {
        'price': 'https://min-api.cryptocompare.com/data/price',
        'histoday': 'https://min-api.cryptocompare.com/data/v2/histoday',
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
        pass
    return None

def collect_binance_ohlcv():
    """Collect OHLCV from Binance (free, no key)."""
    print("\n[BINANCE] OHLCV Data...")
    
    all_data = {}
    
    for pair in FREE_APIS['binance']['pairs']:
        print(f"  Fetching {pair}...")
        
        # Get 1000 candles (max)
        url = f"{FREE_APIS['binance']['base']}/klines"
        params = {
            'symbol': pair,
            'interval': '1d',
            'limit': 1000
        }
        
        data = fetch_json(url, params)
        if data:
            all_data[pair] = data
            print(f"    {pair}: {len(data)} candles")
        
        time.sleep(0.5)
    
    return all_data

def collect_localmonero():
    """Collect XMR stats from LocalMonero."""
    print("\n[LOCALMONERO] XMR Stats...")
    
    data = fetch_json(FREE_APIS['localmonero']['stats'])
    if data:
        print(f"  Height: {data.get('height')}")
        print(f"  Hashrate: {data.get('hashrate')}")
        print(f"  Difficulty: {data.get('difficulty')}")
        print(f"  Emission: {data.get('current_emission')}")
    
    return data

def collect_minexmr():
    """Collect XMR pool stats."""
    print("\n[MINEXMR] Pool Stats...")
    
    data = fetch_json(FREE_APIS['minexmr']['stats'])
    if data:
        pool = data.get('pool', {})
        network = data.get('network', {})
        print(f"  Pool hashrate: {pool.get('hashrate')}")
        print(f"  Active miners: {pool.get('activeMiners')}")
        print(f"  Network difficulty: {network.get('difficulty')}")
        print(f"  Network height: {network.get('height')}")
    
    return data

def collect_coingecko_prices():
    """Collect prices from CoinGecko."""
    print("\n[COINGECKO] Prices...")
    
    coins = ['monero', 'bitcoin', 'ethereum', 'tari', 'xelis', 'nockchain']
    
    params = {
        'ids': ','.join(coins),
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true',
        'include_24hr_change': 'true'
    }
    
    data = fetch_json(FREE_APIS['coingecko']['simple'], params)
    if data:
        for coin, values in data.items():
            print(f"  {coin}: ${values.get('usd', 'N/A')} ({values.get('usd_24h_change', 'N/A'):.2f}%)")
    
    return data

def collect_coincap():
    """Collect from CoinCap (free)."""
    print("\n[COINCAP] Assets...")
    
    assets = ['monero', 'bitcoin', 'ethereum']
    all_data = {}
    
    for asset in assets:
        print(f"  Fetching {asset}...")
        url = f"https://api.coincap.io/v2/assets/{asset}"
        data = fetch_json(url)
        if data and 'data' in data:
            d = data['data']
            print(f"    {asset}: ${d.get('priceUsd', 'N/A')}")
            all_data[asset] = d
        time.sleep(0.5)
    
    return all_data

def collect_cryptocompare():
    """Collect from CryptoCompare (free)."""
    print("\n[CRYPTOCOMPARE] Historical...")
    
    # XMR daily history
    params = {
        'fsym': 'XMR',
        'tsym': 'USD',
        'limit': 365,
        'toTs': int(time.time())
    }
    
    data = fetch_json(FREE_APIS['cryptocompare']['histoday'], params)
    if data and 'Data' in data:
        hist = data['Data'].get('Data', [])
        print(f"  XMR: {len(hist)} daily candles")
        return hist
    
    return None

def collect_all():
    """Collect all free data."""
    print(f"\n{'='*60}")
    print(f"Collecting Free Data — {datetime.now()}")
    print(f"{'='*60}")
    
    all_data = {
        'collected_at': datetime.now().isoformat(),
        'binance_ohlcv': collect_binance_ohlcv(),
        'localmonero': collect_localmonero(),
        'minexmr': collect_minexmr(),
        'coingecko': collect_coingecko_prices(),
        'coincap': collect_coincap(),
        'cryptocompare': collect_cryptocompare(),
    }
    
    # Save
    filepath = os.path.join(DATA_DIR, 'free_data.json')
    with open(filepath, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    print(f"  Size: {os.path.getsize(filepath):,} bytes")
    
    return all_data

if __name__ == '__main__':
    collect_all()
