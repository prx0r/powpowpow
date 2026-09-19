"""
PowPowPow API v2 — Serves pressure equation metrics.
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

FUNDAMENTALS = load_json('chain_fundamentals.json')
GITHUB_STATS = load_json('github_stats.json')
CHAIN_STATS = load_json('real_chain_stats.json')
MINER_REVENUE = load_json('miner_revenue.json')
FACTORS = load_json('factors/cross_chain_factors.json')
ECONOMICS = load_json('economics/miner_economics.json')

# Import modules
from pressure import PressureEquation
from two_timescale import TwoTimescaleModel
from ofi import OFICalculator

# Initialize pressure calculators
pressure_calcs = {}
for symbol in FUNDAMENTALS:
    pressure_calcs[symbol] = PressureEquation(symbol)

@app.route('/')
def index():
    return jsonify({
        'name': 'PowPowPow API v2',
        'version': '2.0.0',
        'description': 'Pressure equation metrics for useful-compute crypto',
        'endpoints': {
            'chains': '/api/v1/chains',
            'chain': '/api/v1/chains/<symbol>',
            'pressure': '/api/v1/chains/<symbol>/pressure',
            'factors': '/api/v1/factors',
            'economics': '/api/v1/economics',
            'ofi': '/api/v1/ofi/<symbol>',
            'predictions': '/api/v1/predictions',
        }
    })

@app.route('/api/v1/chains')
def list_chains():
    """List all chains with summary."""
    chains = []
    for symbol, fund in FUNDAMENTALS.items():
        factor = FACTORS.get(symbol, {})
        chains.append({
            'symbol': symbol,
            'name': fund.get('name'),
            'type': fund.get('type'),
            'consensus': fund.get('consensus'),
            'mining_algo': fund.get('mining_algo'),
            'issuance_usd_24h': factor.get('issuance_usd_24h'),
            'dilution_pressure': factor.get('dilution_pressure'),
            'absorption_ratio': factor.get('absorption_ratio'),
            'github_stars': factor.get('github_stars'),
        })
    return jsonify(chains)

@app.route('/api/v1/chains/<symbol>')
def get_chain(symbol):
    """Get full data for a chain."""
    symbol = symbol.upper()
    if symbol not in FUNDAMENTALS:
        return jsonify({'error': f'Unknown chain: {symbol}'}), 404
    
    return jsonify({
        'symbol': symbol,
        'fundamentals': FUNDAMENTALS.get(symbol),
        'github': GITHUB_STATS.get(symbol),
        'chain_stats': CHAIN_STATS.get(symbol),
        'miner_revenue': MINER_REVENUE.get(symbol),
        'factors': FACTORS.get(symbol),
        'economics': ECONOMICS.get(symbol),
        'timestamp': datetime.now().isoformat(),
    })

@app.route('/api/v1/chains/<symbol>/pressure')
def get_pressure(symbol):
    """Get pressure equation metrics."""
    symbol = symbol.upper()
    
    if symbol not in pressure_calcs:
        return jsonify({'error': f'No pressure data for {symbol}'}), 404
    
    calc = pressure_calcs[symbol]
    
    # Update with available data
    fund = FUNDAMENTALS.get(symbol, {})
    revenue = MINER_REVENUE.get(symbol, {})
    sell_pressure = revenue.get('sell_pressure', {})
    
    calc.update_slow_state({
        'emission_usd_day': sell_pressure.get('daily_emission_usd', 0),
        'miner_exchange_flow_usd_day': sell_pressure.get('daily_sell_pressure_usd', 0),
        'market_cap': revenue.get('market_cap', 0),
    })
    
    # Calculate pressure
    result = calc.calculate_pressure_balance()
    
    return jsonify(result)

@app.route('/api/v1/factors')
def get_factors():
    """Get cross-chain factor table."""
    return jsonify(FACTORS)

@app.route('/api/v1/economics')
def get_economics():
    """Get miner economics for all chains."""
    return jsonify(ECONOMICS)

@app.route('/api/v1/predictions')
def predictions():
    """Get pressure-based predictions."""
    results = []
    
    for symbol in FUNDAMENTALS:
        if symbol in pressure_calcs:
            calc = pressure_calcs[symbol]
            
            # Update with data
            fund = FUNDAMENTALS.get(symbol, {})
            revenue = MINER_REVENUE.get(symbol, {})
            sell_pressure = revenue.get('sell_pressure', {})
            
            calc.update_slow_state({
                'emission_usd_day': sell_pressure.get('daily_emission_usd', 0),
                'miner_exchange_flow_usd_day': sell_pressure.get('daily_sell_pressure_usd', 0),
            })
            
            result = calc.calculate_pressure_balance()
            
            # Determine signal
            balance = result.get('pressure_balance', 1)
            if balance > 1.5:
                signal = 'ABSORPTION_DOMINANT'
            elif balance < 0.5:
                signal = 'SELL_PRESSURE_DOMINANT'
            else:
                signal = 'BALANCED'
            
            results.append({
                'symbol': symbol,
                'name': FUNDAMENTALS[symbol].get('name'),
                'pressure_balance': balance,
                'creation_pressure': result.get('creation_pressure', 0),
                'realization_ratio': result.get('miner_realization_ratio', 0),
                'absorption_ratio': result.get('absorption_ratio', 1),
                'required_buy_flow': result.get('required_buy_flow_zero_return', 0),
                'signal': signal,
            })
    
    # Sort by pressure balance
    results.sort(key=lambda x: x['pressure_balance'])
    
    return jsonify(results)

@app.route('/api/v1/health')
def health():
    """Health check."""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'chains_tracked': len(FUNDAMENTALS),
        'pressure_calculators': len(pressure_calcs),
        'timestamp': datetime.now().isoformat(),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
