"""
PowPowPow API v1
REST + WebSocket for all V1 data.
"""

from flask import Flask, jsonify, request
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/box/powpowpow')

app = Flask(__name__)

BASE_DIR = '/home/box/powpowpow'
CHAINS_DIR = os.path.join(BASE_DIR, 'chains')

# Load all data
def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

CHAIN_DATA = {}
for coin in ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS']:
    data = load_json(f'{coin.lower()}/{coin.lower()}_data.json')
    if data:
        CHAIN_DATA[coin] = data

EXCHANGE_DATA = {
    'gate': load_json('exchanges/gate/gate_data.json'),
    'coinex': load_json('exchanges/coinex/coinex_data.json'),
}

FACTORS = load_json('factors/cross_chain_factors.json')
ECONOMICS = load_json('economics/miner_economics.json')

# V1 Registry
from v1_registry import get_v1_registry
REGISTRY = get_v1_registry()

def success(data, meta=None):
    return jsonify({
        'status': 'ok',
        'data': data,
        'meta': meta or {'timestamp': datetime.now().isoformat()}
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
        data = CHAIN_DATA.get(symbol, {})
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
    data = CHAIN_DATA.get(symbol, {})
    
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
        data = CHAIN_DATA.get(symbol, {})
        price = data.get('price', {})
        
        if price:
            card = generate_card(symbol, price)
            cards[symbol] = card
    
    return success(cards)

@app.route('/v1/cards/<symbol>')
def get_card(symbol):
    symbol = symbol.upper()
    from v1_live_cards import generate_card
    
    data = CHAIN_DATA.get(symbol, {})
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
    return success(list(EXCHANGE_DATA.keys()))

@app.route('/v1/exchanges/<exchange>/markets')
def exchange_markets(exchange):
    data = EXCHANGE_DATA.get(exchange, {})
    return success(data.get('markets', {}))

@app.route('/v1/exchanges/<exchange>/<symbol>/orderbook')
def exchange_orderbook(exchange, symbol):
    symbol = symbol.upper()
    data = EXCHANGE_DATA.get(exchange, {})
    orderbooks = data.get('order_books', {})
    
    if symbol in orderbooks:
        return success(orderbooks[symbol])
    return error(f'No order book for {symbol} on {exchange}', 404)

@app.route('/v1/exchanges/<exchange>/<symbol>/trades')
def exchange_trades(exchange, symbol):
    symbol = symbol.upper()
    data = EXCHANGE_DATA.get(exchange, {})
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
    data = FACTORS.get(symbol, {})
    
    if not data:
        return error(f'No pressure data for {symbol}', 404)
    
    return success(data)

@app.route('/v1/metrics/resource-premium')
def resource_premium():
    premiums = []
    for symbol in REGISTRY:
        econ = ECONOMICS.get(symbol, {})
        if econ:
            premiums.append({
                'chain': symbol,
                'daily_emission_usd': econ.get('daily_emission_usd', 0),
                'absorption_ratio': econ.get('absorption_ratio'),
            })
    return success(premiums)

@app.route('/v1/metrics/miner-economics')
def miner_economics():
    return success(ECONOMICS)

# ============================================================
# FACTORS
# ============================================================

@app.route('/v1/factors')
def factors():
    return success(FACTORS)

# ============================================================
# HEALTH
# ============================================================

@app.route('/v1/health')
def health():
    return success({
        'status': 'healthy',
        'version': '1.0.0',
        'chains_tracked': len(REGISTRY),
        'exchanges_connected': len(EXCHANGE_DATA),
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
    app.run(host='0.0.0.0', port=5000, debug=False)
