"""
Gate.io Exchange Collector
L2 order book + trades for V1 coins.
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
os.makedirs(f'{DATA_DIR}/exchanges/gate', exist_ok=True)

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
    """Discover which V1 coins are listed on Gate."""
    print("  [DISCOVER] Checking Gate markets...")
    
    data = fetch_json('https://api.gateio.ws/api/v4/spot/currency_pairs')
    if not data:
        return {}
    
    # V1 coins to check
    v1_coins = ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS']
    
    markets = {}
    for pair in data:
        symbol = pair.get('base', '').upper()
        if symbol in v1_coins and pair.get('quote') == 'USDT':
            markets[symbol] = {
                'exchange': 'gate',
                'symbol': pair.get('symbol'),
                'base': symbol,
                'quote': 'USDT',
                'status': pair.get('trade_status'),
                'min_amount': pair.get('min_amount'),
                'max_amount': pair.get('max_amount'),
            }
    
    print(f"    Found: {len(markets)} V1 markets on Gate")
    return markets

def collect_order_book(symbol, limit=20):
    """Collect order book from Gate."""
    pair = f'{symbol}_USDT'
    data = fetch_json(f'https://api.gateio.ws/api/v4/spot/order_book', params={
        'currency_pair': pair,
        'limit': limit
    })
    return data

def collect_trades(symbol, limit=100):
    """Collect recent trades from Gate."""
    pair = f'{symbol}_USDT'
    data = fetch_json(f'https://api.gateio.ws/api/v4/spot/trades', params={
        'currency_pair': pair,
        'limit': limit
    })
    return data

def collect_all():
    print(f"\n{'='*60}")
    print(f"Gate.io Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    markets = discover_markets()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'exchange': 'gate',
        'markets': markets,
        'order_books': {},
        'trades': {},
    }
    
    for symbol in markets:
        print(f"  [{symbol}] Collecting...")
        
        ob = collect_order_book(symbol)
        if ob:
            results['order_books'][symbol] = ob
            print(f"    Order book: {len(ob.get('bids', []))} bids, {len(ob.get('asks', []))} asks")
        
        trades = collect_trades(symbol)
        if trades:
            results['trades'][symbol] = trades
            print(f"    Trades: {len(trades)} recent")
        
        time.sleep(0.5)
    
    filepath = f'{DATA_DIR}/exchanges/gate/gate_data.json'
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
