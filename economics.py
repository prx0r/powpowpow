"""
Miner Economics Calculator
Computes miner revenue, sell pressure, profitability.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/box/powpowpow')

CHAINS_DIR = '/home/box/powpowpow/chains'
ECONOMICS_DIR = os.path.join(CHAINS_DIR, 'economics')
os.makedirs(ECONOMICS_DIR, exist_ok=True)

# Load data
def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

FUNDAMENTALS = load_json('chain_fundamentals.json')
MINER_REVENUE = load_json('miner_revenue.json')

# Hardware specifications for profitability calculations
HARDWARE_SPECS = {
    'XMR': {
        'RandomX': {
            'cpu': {'hashrate': 20000, 'power': 100, 'cost': 500},  # 20 KH/s, 100W
            'high_end_cpu': {'hashrate': 100000, 'power': 200, 'cost': 2000},  # 100 KH/s
        }
    },
    'PRL': {
        'PearlHash': {
            'rtx_4080': {'hashrate': 203e12, 'power': 270, 'cost': 1250},  # 203 TH/s
            'cmp_170hx': {'hashrate': 175e12, 'power': 240, 'cost': 4000},  # 175 TH/s
        }
    },
    'XEL': {
        'XelisHash': {
            'rtx_4080': {'hashrate': 10100, 'power': 145, 'cost': 1250},  # 10.1 KH/s
            'cpu': {'hashrate': 500, 'power': 65, 'cost': 300},  # 500 H/s
        }
    },
    'XTM': {
        'RandomX': {
            'cpu': {'hashrate': 10000, 'power': 100, 'cost': 500},  # 10 KH/s
        }
    },
}

# Electricity cost ($/kWh)
ELECTRICITY_COST = 0.10

def calculate_miner_economics(symbol):
    """Calculate detailed miner economics for a chain."""
    fund = FUNDAMENTALS.get(symbol, {})
    revenue = MINER_REVENUE.get(symbol, {})
    
    daily_emission = fund.get('daily_emission', 0) or 0
    price = revenue.get('price', 0) or 0
    daily_emission_usd = daily_emission * price
    
    # Sell pressure estimate
    sell_fraction = 0.6  # Industry average
    daily_sell_pressure = daily_emission_usd * sell_fraction
    
    # Hardware profitability
    hardware_profitability = {}
    if symbol in HARDWARE_SPECS:
        for algo, devices in HARDWARE_SPECS[symbol].items():
            for device, specs in devices.items():
                daily_revenue = (specs['hashrate'] / 1e12) * daily_emission * price if daily_emission else 0
                daily_electricity = (specs['power'] / 1000) * 24 * ELECTRICITY_COST
                daily_profit = daily_revenue - daily_electricity
                
                hardware_profitability[device] = {
                    'hashrate': specs['hashrate'],
                    'power_w': specs['power'],
                    'cost_usd': specs['cost'],
                    'daily_revenue_usd': daily_revenue,
                    'daily_electricity_usd': daily_electricity,
                    'daily_profit_usd': daily_profit,
                    'payback_days': specs['cost'] / daily_profit if daily_profit > 0 else None,
                    'annual_roi': (daily_profit * 365 / specs['cost'] * 100) if specs['cost'] > 0 else None,
                }
    
    economics = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'name': fund.get('name'),
        
        # Emission
        'daily_emission': daily_emission,
        'daily_emission_usd': daily_emission_usd,
        'annual_emission_usd': daily_emission_usd * 365,
        
        # Sell pressure
        'sell_fraction': sell_fraction,
        'daily_sell_pressure_usd': daily_sell_pressure,
        'annual_sell_pressure_usd': daily_sell_pressure * 365,
        
        # Absorption
        'volume_24h': revenue.get('volume_24h', 0),
        'absorption_ratio': revenue.get('volume_24h', 0) / daily_emission_usd if daily_emission_usd > 0 else None,
        
        # Dilution
        'market_cap': revenue.get('market_cap', 0),
        'dilution_pressure': revenue.get('miner_burden', {}).get('dilution_pressure'),
        
        # Hardware
        'hardware_profitability': hardware_profitability,
        
        # Electricity
        'electricity_cost_kwh': ELECTRICITY_COST,
    }
    
    return economics

def calculate_all():
    """Calculate economics for all chains."""
    print(f"\n{'='*60}")
    print(f"Calculating Miner Economics — {datetime.now()}")
    print(f"{'='*60}")
    
    all_economics = {}
    
    for symbol in FUNDAMENTALS:
        print(f"\n[{symbol}]")
        try:
            economics = calculate_miner_economics(symbol)
            all_economics[symbol] = economics
            
            print(f"  Daily emission: ${economics['daily_emission_usd']:,.0f}")
            print(f"  Daily sell pressure: ${economics['daily_sell_pressure_usd']:,.0f}")
            print(f"  Absorption: {economics['absorption_ratio']:.1f}x" if economics['absorption_ratio'] else "  Absorption: N/A")
            
            if economics['hardware_profitability']:
                print("  Hardware profitability:")
                for device, prof in economics['hardware_profitability'].items():
                    print(f"    {device}: ${prof['daily_profit_usd']:.2f}/day, {prof['payback_days']:.0f} days payback" if prof['payback_days'] else f"    {device}: ${prof['daily_profit_usd']:.2f}/day")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save
    output_file = os.path.join(ECONOMICS_DIR, 'miner_economics.json')
    with open(output_file, 'w') as f:
        json.dump(all_economics, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    return all_economics

if __name__ == '__main__':
    calculate_all()
