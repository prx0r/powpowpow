"""

STALE 2026-09-25: parked. Superseded by site/server.py on
127.0.0.1:8795 (pow-site.service). The bind below was 0.0.0.0:5000 with
no auth — anyone on the LAN could read it. It is loopback-only now.
Endpoint ideas only; do not deploy.
PowPowPow API v1
REST + WebSocket for all V1 data.
"""

from flask import Flask, jsonify, request
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

app = Flask(__name__)

CHAINS_DIR = os.path.join(BASE_DIR, 'chains')

# Load all data — LAZY per request (never import-time cache; the old
# import-time snapshot could serve stale data forever).
def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def chain_data():
    out = {}
    for coin in ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS']:
        data = load_json(f'{coin.lower()}/{coin.lower()}_data.json')
        if data:
            out[coin] = data
    return out

def exchange_data():
    return {
        'gate': load_json('exchanges/gate/gate_data.json'),
        'coinex': load_json('exchanges/coinex/coinex_data.json'),
    }

# V1 Registry — single source of truth for the 8-system V1 universe
from v1_registry import get_v1
REGISTRY = get_v1()

def success(data, meta=None):
    return jsonify({
        'status': 'ok',
        'data': data,
        'meta': meta or {'timestamp': datetime.now(timezone.utc).isoformat()}
    })

def error(message, code=400):
    return jsonify({'status': 'error', 'message': message}), code

# ============================================================
# CHAINS
# ============================================================

@app.route('/v1/chains')
def list_chains():
    chains = []
    for symbol, info in REGISTRY.items():
        data = chain_data().get(symbol, {})
        price = data.get('price', {})
        price_usd = price.get('usd', 0) if isinstance(price, dict) else price
        
        chains.append({
            'symbol': symbol,
            'name': info.get('name', symbol),
            'category': info.get('category', 'unknown'),
            'physical_resource': info.get('physical_resource', 'unknown'),
            'supplier_type': info.get('supplier_type', 'unknown'),
            'price_usd': price_usd,
        })
    return success(chains)

@app.route('/v1/chains/<symbol>')
def get_chain(symbol):
    symbol = symbol.upper()
    if symbol not in REGISTRY:
        return error(f'Unknown chain: {symbol}', 404)
    
    info = REGISTRY[symbol]
    data = chain_data().get(symbol, {})
    
    return success({
        'symbol': symbol,
        'info': info,
        'data': data,
    })

# ============================================================
# LIVE CARDS
# ============================================================

@app.route('/v1/cards')
def list_cards():
    from v1_live_cards import generate_card
    
    cards = {}
    for symbol in REGISTRY:
        data = chain_data().get(symbol, {})
        price = data.get('price', {})
        
        if price:
            card = generate_card(symbol, price)
            cards[symbol] = card
    
    return success(cards)

@app.route('/v1/cards/<symbol>')
def get_card(symbol):
    symbol = symbol.upper()
    from v1_live_cards import generate_card
    
    data = chain_data().get(symbol, {})
    price = data.get('price', {})
    
    if not price:
        return error(f'No price data for {symbol}', 404)
    
    card = generate_card(symbol, price)
    return success(card)

# ============================================================
# COMPUTE MARKETS
# ============================================================

@app.route('/v1/compute/markets')
def compute_markets():
    return success({
        'akash': load_json('akt/akt_data.json'),
        'clore': load_json('clore/clore_data.json'),
        'nosana': load_json('nos/nos_data.json'),
    })

@app.route('/v1/compute/benchmarks')
def compute_benchmarks():
    return success(load_json('benchmarks/compute_benchmarks.json'))

# ============================================================
# EXCHANGES
# ============================================================

@app.route('/v1/exchanges')
def list_exchanges():
    return success(list(exchange_data().keys()))

@app.route('/v1/exchanges/<exchange>/markets')
def exchange_markets(exchange):
    data = exchange_data().get(exchange, {})
    return success(data.get('markets', {}))

@app.route('/v1/exchanges/<exchange>/<symbol>/orderbook')
def exchange_orderbook(exchange, symbol):
    symbol = symbol.upper()
    data = exchange_data().get(exchange, {})
    orderbooks = data.get('order_books', {})
    
    if symbol in orderbooks:
        return success(orderbooks[symbol])
    return error(f'No order book for {symbol} on {exchange}', 404)

@app.route('/v1/exchanges/<exchange>/<symbol>/trades')
def exchange_trades(exchange, symbol):
    symbol = symbol.upper()
    data = exchange_data().get(exchange, {})
    trades = data.get('trades', {})
    
    if symbol in trades:
        return success(trades[symbol])
    return error(f'No trades for {symbol} on {exchange}', 404)

# ============================================================
# METRICS
# ============================================================

@app.route('/v1/metrics/pressure/<symbol>')
def pressure_metrics(symbol):
    symbol = symbol.upper()
    data = load_json('factors/cross_chain_factors.json').get(symbol, {})
    
    if not data:
        return error(f'No pressure data for {symbol}', 404)
    
    return success(data)

@app.route('/v1/metrics/resource-premium')
def resource_premium():
    premiums = []
    for symbol in REGISTRY:
        econ = load_json('economics/miner_economics.json').get(symbol, {})
        if econ:
            premiums.append({
                'chain': symbol,
                'daily_emission_usd': econ.get('daily_emission_usd', 0),
                'absorption_ratio': econ.get('absorption_ratio'),
            })
    return success(premiums)

@app.route('/v1/metrics/miner-economics')
def miner_economics():
    return success(load_json('economics/miner_economics.json'))

# ============================================================
# FACTORS
# ============================================================

@app.route('/v1/factors')
def factors():
    return success(load_json('factors/cross_chain_factors.json'))

# ============================================================
# HEALTH
# ============================================================

@app.route('/v1/health')
def health():
    return success({
        'status': 'healthy',
        'version': '1.0.0',
        'chains_tracked': len(REGISTRY),
        'exchanges_connected': len(exchange_data()),
        'timestamp': datetime.now().isoformat(),
    })

@app.route('/')
def index():
    return success({
        'name': 'PowPowPow API',
        'version': '1.0.0',
        'docs': '/v1/docs',
        'endpoints': [
            '/v1/chains',
            '/v1/cards',
            '/v1/compute/markets',
            '/v1/exchanges',
            '/v1/metrics/pressure/{symbol}',
            '/v1/metrics/resource-premium',
            '/v1/factors',
        ]
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
