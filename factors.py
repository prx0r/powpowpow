"""
Cross-Chain Factor Table Builder
Computes comparable metrics across all chains.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/box/powpowpow')

CHAINS_DIR = '/home/box/powpowpow/chains'
FACTORS_DIR = os.path.join(CHAINS_DIR, 'factors')
os.makedirs(FACTORS_DIR, exist_ok=True)

# Load all data
def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

FUNDAMENTALS = load_json('chain_fundamentals.json')
MINER_REVENUE = load_json('miner_revenue.json')
GITHUB_STATS = load_json('github_stats.json')

def compute_factors():
    """Compute cross-chain factors."""
    print(f"\n{'='*60}")
    print(f"Computing Cross-Chain Factors — {datetime.now()}")
    print(f"{'='*60}")
    
    factors = {}
    
    for symbol in FUNDAMENTALS:
        fund = FUNDAMENTALS[symbol]
        revenue = MINER_REVENUE.get(symbol, {})
        github = GITHUB_STATS.get(symbol, {})
        
        sell_pressure = revenue.get('sell_pressure', {})
        miner_burden = revenue.get('miner_burden', {})
        
        # Basic metrics
        daily_emission_usd = sell_pressure.get('daily_emission_usd', 0) or 0
        market_cap = revenue.get('market_cap', 0) or 0
        volume_24h = revenue.get('volume_24h', 0) or 0
        
        # Factor calculations
        factors[symbol] = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'name': fund.get('name'),
            'chain_type': fund.get('type'),
            
            # Issuance factors
            'issuance_usd_24h': daily_emission_usd,
            'issuance_to_mcap': daily_emission_usd / market_cap if market_cap > 0 else None,
            'issuance_to_volume': daily_emission_usd / volume_24h if volume_24h > 0 else None,
            
            # Sell pressure factors
            'sell_pressure_usd_24h': sell_pressure.get('daily_sell_pressure_usd', 0),
            'sell_fraction': sell_pressure.get('sell_fraction', 0.6),
            
            # Dilution factors
            'dilution_pressure': miner_burden.get('dilution_pressure'),
            'absorption_ratio': miner_burden.get('absorption_ratio'),
            
            # Supply factors
            'max_supply': fund.get('max_supply'),
            'circulating_supply': revenue.get('circulating_supply'),
            'supply_issued_pct': (revenue.get('circulating_supply', 0) / fund.get('max_supply', 1) * 100) if fund.get('max_supply') else None,
            
            # Mining factors
            'mining_algo': fund.get('mining_algo'),
            'useful_output': fund.get('useful_output'),
            'block_time': fund.get('block_time'),
            
            # Development factors
            'github_stars': github.get('total_stars', 0),
            'github_commits_7d': github.get('total_commits_7d', 0),
            'active_developers': github.get('active_developers', 0),
            
            # Derived factors
            'security_spend_usd_24h': daily_emission_usd,  # XMR-style comparison
            'compute_efficiency': None,  # Needs external compute data
            'fundamental_momentum': None,  # Needs historical data
        }
        
        # Print summary
        f = factors[symbol]
        print(f"\n[{symbol}] {fund.get('name')}")
        print(f"  Issuance: ${f['issuance_usd_24h']:,.0f}/day")
        print(f"  Dilution: {f['dilution_pressure']:.4%}/yr" if f['dilution_pressure'] else "  Dilution: N/A")
        print(f"  Absorption: {f['absorption_ratio']:.1f}x" if f['absorption_ratio'] else "  Absorption: N/A")
        print(f"  Sell pressure: ${f['sell_pressure_usd_24h']:,.0f}/day")
        print(f"  GitHub: {f['github_stars']} stars, {f['github_commits_7d']} commits/7d")
    
    # Save factors
    output_file = os.path.join(FACTORS_DIR, 'cross_chain_factors.json')
    with open(output_file, 'w') as f:
        json.dump(factors, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    # Create comparison table
    print(f"\n{'='*60}")
    print("CROSS-CHAIN COMPARISON")
    print(f"{'='*60}")
    print(f"{'Symbol':8} {'Name':12} {'Issuance $/d':>14} {'Dilution':>10} {'Absorption':>12} {'GitHub':>8}")
    print("-" * 70)
    
    for symbol, f in sorted(factors.items(), key=lambda x: x[1].get('issuance_usd_24h', 0) or 0, reverse=True):
        issuance = f"${f['issuance_usd_24h']:,.0f}" if f['issuance_usd_24h'] else "N/A"
        dilution = f"{f['dilution_pressure']:.2%}" if f['dilution_pressure'] else "N/A"
        absorption = f"{f['absorption_ratio']:.1f}x" if f['absorption_ratio'] else "N/A"
        github = f"{f['github_stars']}"
        
        print(f"{symbol:8} {f['name']:12} {issuance:>14} {dilution:>10} {absorption:>12} {github:>8}")
    
    return factors

if __name__ == '__main__':
    compute_factors()
