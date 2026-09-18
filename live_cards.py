"""
Live Card Builder
Generates hardware profitability cards for V1 systems.
"""

import json
import os
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')

# Hardware specs (public benchmarks)
HARDWARE = {
    'PRL': {
        'H100': {'hashrate': 3000e12, 'power': 700, 'cost': 30000, 'algo': 'PearlHash'},
        'H200': {'hashrate': 4000e12, 'power': 700, 'cost': 40000, 'algo': 'PearlHash'},
        'RTX_4090': {'hashrate': 250e12, 'power': 450, 'cost': 2000, 'algo': 'PearlHash'},
    },
    'QUBIC': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'Useful PoW'},
        'EPYC_7763': {'hashrate': 45000, 'power': 280, 'cost': 3000, 'algo': 'Useful PoW'},
    },
    'XMR': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'RandomX'},
        'Ryzen_7_7800X3D': {'hashrate': 15000, 'power': 120, 'cost': 400, 'algo': 'RandomX'},
    },
    'KAS': {
        'KS5_Pro': {'hashrate': 21e15, 'power': 3150, 'cost': 15000, 'algo': 'kHeavyHash'},
        'KS3_Pro': {'hashrate': 9.4e12, 'power': 3400, 'cost': 8000, 'algo': 'kHeavyHash'},
    },
}

# Electricity default
ELECTRICITY = 0.10  # $/kWh

# Hardware depreciation (years)
DEPRECIATION_YEARS = 3

def build_card(coin, price, hashrate=None, difficulty=None, emission=None):
    """Build a live profitability card for a coin."""
    # Handle dict price
    if isinstance(price, dict):
        price_val = float(price.get('usd', 0) or 0)
    else:
        price_val = float(price or 0)
    
    card = {
        'coin': coin,
        'timestamp': datetime.now().isoformat(),
        'price': price_val,
    }
    
    if coin in HARDWARE:
        print(f"\n{'='*50}")
        print(f"{coin} — Hardware Profitability Card")
        print(f"{'='*50}")
        print(f"Price: ${price_val:.8f}")
        print()
        
        for hw_name, specs in HARDWARE[coin].items():
            # Calculate profitability
            daily_electricity = (specs['power'] / 1000) * 24 * ELECTRICITY
            daily_hw_cost = specs['cost'] / (DEPRECIATION_YEARS * 365)
            
            # Revenue depends on coin
            if coin == 'PRL':
                # PRL: hashrate in TH/s
                daily_revenue = (specs['hashrate'] / 1e12) * 0.0000001 * price_val * 86400  # Simplified
            elif coin == 'XMR':
                # XMR: hashrate in H/s, ~0.00006 XMR/kH/s/day
                daily_revenue = (specs['hashrate'] / 1000) * 0.00006 * price_val
            elif coin == 'KAS':
                # KAS: hashrate in TH/s
                daily_revenue = (specs['hashrate'] / 1e12) * 100 * price_val  # Simplified
            else:
                daily_revenue = 0
            
            daily_profit = daily_revenue - daily_electricity - daily_hw_cost
            
            print(f"  {hw_name}:")
            print(f"    Hashrate:     {specs['hashrate']:,.0f} H/s")
            print(f"    Power:        {specs['power']}W")
            print(f"    Cost:         ${specs['cost']:,}")
            print(f"    Revenue/day:  ${daily_revenue:.2f}")
            print(f"    Electricity:  ${daily_electricity:.2f}/day")
            print(f"    HW amort:     ${daily_hw_cost:.2f}/day")
            print(f"    Net profit:   ${daily_profit:.2f}/day")
            print(f"    Payback:      {specs['cost']/daily_profit:.0f} days" if daily_profit > 0 else "    Payback:      Never")
            print()
            
            card[hw_name] = {
                'hashrate': specs['hashrate'],
                'power': specs['power'],
                'cost': specs['cost'],
                'daily_revenue': daily_revenue,
                'daily_electricity': daily_electricity,
                'daily_hw_cost': daily_hw_cost,
                'daily_profit': daily_profit,
            }
    
    return card

def build_all_cards():
    """Build cards for all V1 coins with known prices."""
    print(f"\n{'='*60}")
    print(f"V1 Live Cards — {datetime.now()}")
    print(f"{'='*60}")
    
    # Load prices
    prices_file = '/home/box/powpowpow/historical_data/external/external_data.json'
    if os.path.exists(prices_file):
        with open(prices_file) as f:
            ext_data = json.load(f)
        prices = ext_data.get('prices', {})
    else:
        prices = {}
    
    # Also load from free_data
    free_file = '/home/box/powpowpow/historical_data/free_data.json'
    if os.path.exists(free_file):
        with open(free_file) as f:
            free_data = json.load(f)
        coingecko = free_data.get('coingecko', {})
        for symbol, data in coingecko.items():
            if isinstance(data, dict) and 'usd' in data:
                prices[symbol.upper()] = data['usd']
    
    # Build cards for coins with hardware specs
    for coin in ['PRL', 'XMR', 'KAS']:
        price_data = prices.get(coin, 0)
        if price_data:
            build_card(coin, price_data)
    
    print(f"\n{'='*60}")
    print("V1 Summary")
    print(f"{'='*60}")
    for coin in ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS']:
        price_data = prices.get(coin, 'N/A')
        if isinstance(price_data, dict):
            price_val = price_data.get('usd', 'N/A')
        else:
            price_val = price_data
        print(f"  {coin:8} ${price_val}")

if __name__ == '__main__':
    build_all_cards()
