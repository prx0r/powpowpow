"""
CoinEx Exchange Collector — SUPERSEDED for L2 by collectors/venue_l2.py
(continuous, gap-safe, raw-archived). Kept for one-shot market discovery
checks only. Do not build on its overwrite-style coinex_data.json output.
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

DATA_DIR = os.path.join(BASE_DIR, 'chains')
os.makedirs(f'{DATA_DIR}/exchanges/coinex', exist_ok=True)

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

def discover_markets():
    """Discover V1 coins on CoinEx."""
    print("  [DISCOVER] Checking CoinEx markets...")
    
    data = fetch_json('https://api.coinex.com/v2/spot/market')
    if not data or 'data' not in data:
        return {}
    
    v1_coins = ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS']
    markets = {}
    
    for market in data.get('data', []):
        symbol = market.get('base_ccy', '').upper()
        if symbol in v1_coins and market.get('quote_ccy') == 'USDT':
            markets[symbol] = {
                'exchange': 'coinex',
                'symbol': market.get('market_name'),
                'base': symbol,
                'quote': 'USDT',
                'status': 'trading',
            }
    
    print(f"    Found: {len(markets)} V1 markets on CoinEx")
    return markets

def collect_order_book(symbol, limit=20):
    """Collect order book from CoinEx."""
    market = f'{symbol}USDT'
    data = fetch_json(f'https://api.coinex.com/v2/spot/order_book', params={
        'market': market,
        'limit': limit,
        'depth': 'full'
    })
    return data

def collect_trades(symbol, limit=100):
    """Collect recent trades from CoinEx."""
    market = f'{symbol}USDT'
    data = fetch_json(f'https://api.coinex.com/v2/spot/trades', params={
        'market': market,
        'limit': limit
    })
    return data

def collect_all():
    print(f"\n{'='*60}")
    print(f"CoinEx Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    markets = discover_markets()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'exchange': 'coinex',
        'markets': markets,
        'order_books': {},
        'trades': {},
    }
    
    for symbol in markets:
        print(f"  [{symbol}] Collecting...")
        
        ob = collect_order_book(symbol)
        if ob:
            results['order_books'][symbol] = ob
            print(f"    Order book: collected")
        
        trades = collect_trades(symbol)
        if trades:
            results['trades'][symbol] = trades
            print(f"    Trades: collected")
        
        time.sleep(0.5)
    
    filepath = f'{DATA_DIR}/exchanges/coinex/coinex_data.json'
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
