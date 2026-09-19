"""
PowPowPow API — Simple Flask API for live data and predictions.
"""

from flask import Flask, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)

import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Legacy flat-file dir (old /home/box tracker) still honored via env;
# default is the warehouse normalized tables written by venue_l2.
DATA_DIR = os.environ.get('SAFETRADE_TRACKED_DIR', '')

COINS = {
    'QUBIC': {'name': 'Qubic', 'type': 'useful-compute', 'market': 'qubicusdt'},
    'PRL': {'name': 'Pearl', 'type': 'useful-compute', 'market': 'prlusdt'},
    'NOCK': {'name': 'Nockchain', 'type': 'zk-pow', 'market': 'nockusdt'},
    'XMR': {'name': 'Monero', 'type': 'privacy', 'market': 'xmrusdt'},
    'GNK': {'name': 'Gonka', 'type': 'compute-market', 'market': 'gnkusdt'},
    'TSC': {'name': 'TensorCash', 'type': 'ai-inference', 'market': 'tscusdt'},
    'XEL': {'name': 'Xelis', 'type': 'privacy-dag', 'market': 'xelusdt'},
    'XTM': {'name': 'Tari', 'type': 'privacy', 'market': 'xtmusdt'},
    'NPT': {'name': 'Neptune', 'type': 'privacy-stark', 'market': 'nptusdt'},
    'QTC': {'name': 'Qubitcoin', 'type': 'quantum-sim', 'market': 'qtcusdt'},
}

def load_latest_depth(coin):
    # 1. Legacy flat files if a tracked dir is configured
    if DATA_DIR and os.path.isdir(DATA_DIR):
        files = [f for f in os.listdir(DATA_DIR)
                 if f.startswith(f'{coin}_depth') and f.endswith('.json')]
        if files:
            with open(os.path.join(DATA_DIR, sorted(files)[-1])) as f:
                data = json.load(f)
            return data[-1] if isinstance(data, list) and data else data
    # 2. Warehouse: latest orderbook_snapshot for this symbol, any venue
    best = None
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', 'orderbook_snapshot',
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (r.get('symbol') or '').upper() != coin:
                        continue
                    if best is None or r.get('receive_time', '') > best.get('receive_time', ''):
                        best = r
    if best:
        return {'bids': best.get('bids', []), 'asks': best.get('asks', []),
                'timestamp': best.get('receive_time'),
                'venue': best.get('venue'), 'mid': best.get('mid')}
    return None

@app.route('/')
def index():
    return jsonify({
        'name': 'PowPowPow API',
        'version': '0.1.0',
        'description': 'Data infrastructure for useful-compute crypto',
        'endpoints': [
            '/api/v1/chains',
            '/api/v1/chains/<coin>',
            '/api/v1/chains/<coin>/orderbook',
            '/api/v1/chains/<coin>/features',
            '/api/v1/predictions',
            '/api/v1/status',
        ]
    })

@app.route('/api/v1/chains')
def chains():
    result = []
    for symbol, info in COINS.items():
        depth = load_latest_depth(symbol)
        mid_price = 0
        imbalance = 0
        if depth:
            bids = depth.get('bids', [])
            asks = depth.get('asks', [])
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                mid_price = (best_bid + best_ask) / 2
                bid_vol = sum(float(b[1]) for b in bids)
                ask_vol = sum(float(a[1]) for a in asks)
                total = bid_vol + ask_vol
                imbalance = (bid_vol - ask_vol) / total if total else 0
        
        result.append({
            'symbol': symbol,
            'name': info['name'],
            'type': info['type'],
            'mid_price': mid_price,
            'imbalance': imbalance,
            'has_depth': depth is not None
        })
    return jsonify(result)

@app.route('/api/v1/chains/<coin>')
def chain_detail(coin):
    coin = coin.upper()
    if coin not in COINS:
        return jsonify({'error': 'Unknown coin'}), 404
    
    info = COINS[coin]
    depth = load_latest_depth(coin)
    
    result = {
        'symbol': coin,
        'name': info['name'],
        'type': info['type'],
        'orderbook': None
    }
    
    if depth:
        bids = depth.get('bids', [])
        asks = depth.get('asks', [])
        
        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        total = bid_vol + ask_vol
        
        result['orderbook'] = {
            'best_bid': float(bids[0][0]) if bids else 0,
            'best_ask': float(asks[0][0]) if asks else 0,
            'spread': float(asks[0][0]) - float(bids[0][0]) if bids and asks else 0,
            'bid_volume': bid_vol,
            'ask_volume': ask_vol,
            'imbalance': (bid_vol - ask_vol) / total if total else 0,
            'num_bids': len(bids),
            'num_asks': len(asks),
            'timestamp': depth.get('timestamp')
        }
    
    return jsonify(result)

@app.route('/api/v1/chains/<coin>/orderbook')
def orderbook(coin):
    coin = coin.upper()
    depth = load_latest_depth(coin)
    if not depth:
        return jsonify({'error': 'No data'}), 404
    return jsonify(depth)

@app.route('/api/v1/predictions')
def predictions():
    """Simple imbalance-based predictions."""
    results = []
    for symbol in COINS:
        depth = load_latest_depth(symbol)
        if not depth:
            continue
        
        bids = depth.get('bids', [])
        asks = depth.get('asks', [])
        
        if not bids or not asks:
            continue
        
        bid_vol = sum(float(b[1]) for b in bids)
        ask_vol = sum(float(a[1]) for a in asks)
        total = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total if total else 0
        
        if imbalance > 0.2:
            signal = 'BULLISH'
        elif imbalance < -0.2:
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        results.append({
            'symbol': symbol,
            'imbalance': imbalance,
            'signal': signal,
            'bid_volume': bid_vol,
            'ask_volume': ask_vol
        })
    
    return jsonify(results)

@app.route('/api/v1/status')
def status():
    files = 0
    for chain in ('venue', 'safetrade'):
        snap_dir = os.path.join(BASE_DIR, 'warehouse', 'normalized', 'orderbook_snapshot', f'chain={chain}')
        if os.path.isdir(snap_dir):
            for _root, _dirs, _fs in os.walk(snap_dir):
                files += sum(1 for _f in _fs if _f.endswith('.jsonl'))
    return jsonify({
        'collector': 'running',
        'coins_tracked': len(COINS),
        'data_files': files,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
