"""
PowPowPow API — Serves all chain data via REST.
"""

from flask import Flask, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)

BASE_DIR = '/home/box/powpowpow'
CHAINS_DIR = os.path.join(BASE_DIR, 'chains')

# Load all data on startup
def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# Preload data
FUNDAMENTALS = load_json('chain_fundamentals.json')
GITHUB_STATS = load_json('github_stats.json')
CHAIN_STATS = load_json('real_chain_stats.json')
MINER_REVENUE = load_json('miner_revenue.json')

# Import data sources
import sys
sys.path.insert(0, BASE_DIR)
from data_sources import DATA_SOURCES

@app.route('/')
def index():
    return jsonify({
        'name': 'PowPowPow API',
        'version': '1.0.0',
        'description': 'Data infrastructure for useful-compute crypto',
        'endpoints': {
            'chains': '/api/v1/chains',
            'chain': '/api/v1/chains/<symbol>',
            'fundamentals': '/api/v1/chains/<symbol>/fundamentals',
            'mining': '/api/v1/chains/<symbol>/mining',
            'github': '/api/v1/chains/<symbol>/github',
            'orderbook': '/api/v1/chains/<symbol>/orderbook',
            'predictions': '/api/v1/predictions',
            'sources': '/api/v1/chains/<symbol>/sources',
            'all': '/api/v1/all',
        }
    })

@app.route('/api/v1/chains')
def list_chains():
    """List all tracked chains with summary."""
    chains = []
    for symbol, fund in FUNDAMENTALS.items():
        market = MINER_REVENUE.get(symbol, {})
        chains.append({
            'symbol': symbol,
            'name': fund.get('name'),
            'type': fund.get('type'),
            'consensus': fund.get('consensus'),
            'mining_algo': fund.get('mining_algo'),
            'max_supply': fund.get('max_supply'),
            'daily_emission': fund.get('daily_emission'),
            'daily_emission_usd': market.get('sell_pressure', {}).get('daily_emission_usd'),
            'safe_trade_volume_24h': fund.get('safe_trade_volume_24h'),
            'github_stars': fund.get('github_stars'),
        })
    return jsonify(chains)

@app.route('/api/v1/chains/<symbol>')
def get_chain(symbol):
    """Get full data for a single chain."""
    symbol = symbol.upper()
    if symbol not in FUNDAMENTALS:
        return jsonify({'error': f'Unknown chain: {symbol}'}), 404
    
    result = {
        'symbol': symbol,
        'fundamentals': FUNDAMENTALS.get(symbol),
        'github': GITHUB_STATS.get(symbol),
        'chain_stats': CHAIN_STATS.get(symbol),
        'miner_revenue': MINER_REVENUE.get(symbol),
        'data_sources': DATA_SOURCES.get(symbol),
        'timestamp': datetime.now().isoformat(),
    }
    
    return jsonify(result)

@app.route('/api/v1/chains/<symbol>/fundamentals')
def get_fundamentals(symbol):
    """Get chain fundamentals."""
    symbol = symbol.upper()
    return jsonify(FUNDAMENTALS.get(symbol, {}))

@app.route('/api/v1/chains/<symbol>/mining')
def get_mining(symbol):
    """Get mining economics data."""
    symbol = symbol.upper()
    return jsonify(MINER_REVENUE.get(symbol, {}))

@app.route('/api/v1/chains/<symbol>/github')
def get_github(symbol):
    """Get GitHub activity data."""
    symbol = symbol.upper()
    return jsonify(GITHUB_STATS.get(symbol, {}))

@app.route('/api/v1/chains/<symbol>/sources')
def get_sources(symbol):
    """Get data sources for a chain."""
    symbol = symbol.upper()
    sources = DATA_SOURCES.get(symbol, {})
    return jsonify(sources)

@app.route('/api/v1/predictions')
def predictions():
    """Simple predictions based on miner sell pressure."""
    results = []
    for symbol, revenue in MINER_REVENUE.items():
        sell = revenue.get('sell_pressure', {})
        burden = revenue.get('miner_burden', {})
        
        if sell.get('daily_sell_pressure_usd'):
            daily_sell = sell['daily_sell_pressure_usd']
            volume = revenue.get('volume_24h', 0) or 0
            
            if volume > 0:
                sell_ratio = daily_sell / volume
                if sell_ratio > 0.5:
                    signal = 'HIGH_SELL_PRESSURE'
                elif sell_ratio > 0.2:
                    signal = 'MODERATE_SELL_PRESSURE'
                else:
                    signal = 'LOW_SELL_PRESSURE'
            else:
                signal = 'NO_VOLUME_DATA'
            
            results.append({
                'symbol': symbol,
                'daily_sell_pressure': daily_sell,
                'volume_24h': volume,
                'sell_ratio': sell_ratio if volume > 0 else None,
                'signal': signal,
                'dilution_pressure': burden.get('dilution_pressure'),
                'absorption_ratio': burden.get('absorption_ratio'),
            })
    
    return jsonify(results)

@app.route('/api/v1/all')
def get_all():
    """Get everything for all chains."""
    result = {}
    for symbol in FUNDAMENTALS:
        result[symbol] = {
            'fundamentals': FUNDAMENTALS.get(symbol),
            'github': GITHUB_STATS.get(symbol),
            'miner_revenue': MINER_REVENUE.get(symbol),
            'sources_count': len(DATA_SOURCES.get(symbol, {}).get('apis', [])),
        }
    return jsonify(result)

@app.route('/api/v1/health')
def health():
    """Health check."""
    return jsonify({
        'status': 'healthy',
        'chains_tracked': len(FUNDAMENTALS),
        'timestamp': datetime.now().isoformat(),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
