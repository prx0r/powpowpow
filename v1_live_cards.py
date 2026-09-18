"""
V1 Live Card Generator
Produces hardware profitability cards for all V1 chains.
"""

import json
import os
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')

# V1 Chains with their hardware
V1_HARDWARE = {
    'PRL': {
        'H100': {'hashrate': 3000e12, 'power': 700, 'cost': 30000, 'algo': 'PearlHash', 'yield_per_th': 0.0000001},
        'H200': {'hashrate': 4000e12, 'power': 700, 'cost': 40000, 'algo': 'PearlHash', 'yield_per_th': 0.0000001},
        'RTX_4090': {'hashrate': 250e12, 'power': 450, 'cost': 2000, 'algo': 'PearlHash', 'yield_per_th': 0.0000001},
    },
    'QUBIC': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'Useful PoW', 'yield_per_h': 0.000001},
        'EPYC_7763': {'hashrate': 45000, 'power': 280, 'cost': 3000, 'algo': 'Useful PoW', 'yield_per_h': 0.000001},
    },
    'XMR': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'RandomX', 'yield_per_h': 0.00006},
        'Ryzen_7_7800X3D': {'hashrate': 15000, 'power': 120, 'cost': 400, 'algo': 'RandomX', 'yield_per_h': 0.00006},
    },
    'KAS': {
        'KS5_Pro': {'hashrate': 21e15, 'power': 3150, 'cost': 15000, 'algo': 'kHeavyHash', 'yield_per_th': 50},
        'KS3_L': {'hashrate': 6e12, 'power': 3400, 'cost': 5000, 'algo': 'kHeavyHash', 'yield_per_th': 50},
    },
    'QUAN': {
        'RTX_4090': {'hashrate': 1e9, 'power': 450, 'cost': 2000, 'algo': 'Poseidon2', 'yield_per_h': 0.001},
    },
    'CLORE': {
        'RTX_4090': {'hashrate': 0, 'power': 450, 'cost': 2000, 'algo': 'rental', 'rental_per_hour': 0.50},
    },
    'AKT': {
        'H100': {'hashrate': 0, 'power': 700, 'cost': 30000, 'algo': 'rental', 'rental_per_hour': 2.50},
    },
    'NOS': {
        'H100': {'hashrate': 0, 'power': 700, 'cost': 30000, 'algo': 'inference', 'rental_per_hour': 2.00},
    },
}

# Defaults
ELECTRICITY = 0.10  # $/kWh
DEPRECIATION_YEARS = 3

def generate_card(chain, price, network_data=None):
    """Generate a live card for a chain."""
    if isinstance(price, dict):
        price = float(price.get('usd', 0) or 0)
    
    card = {
        'coin': chain,
        'timestamp': datetime.now().isoformat(),
        'price_usd': price,
        'hardware': {}
    }
    
    if chain in V1_HARDWARE:
        for hw_name, specs in V1_HARDWARE[chain].items():
            daily_electricity = (specs['power'] / 1000) * 24 * ELECTRICITY
            daily_hw_cost = specs['cost'] / (DEPRECIATION_YEARS * 365)
            
            if specs.get('algo') == 'rental':
                # Rental income model
                daily_revenue = specs.get('rental_per_hour', 0) * 24
            elif specs.get('algo') == 'inference':
                # Inference income model
                daily_revenue = specs.get('rental_per_hour', 0) * 24
            else:
                # Mining income model
                if specs['hashrate'] > 1e12:
                    daily_revenue = (specs['hashrate'] / 1e12) * specs.get('yield_per_th', 0) * price * 86400
                else:
                    daily_revenue = (specs['hashrate'] / 1000) * specs.get('yield_per_h', 0) * price
            
            daily_profit = daily_revenue - daily_electricity - daily_hw_cost
            
            card['hardware'][hw_name] = {
                'hashrate': specs['hashrate'],
                'power_watts': specs['power'],
                'cost_usd': specs['cost'],
                'algo': specs['algo'],
                'revenue_usd_day': round(daily_revenue, 2),
                'electricity_usd_day': round(daily_electricity, 2),
                'hw_amort_usd_day': round(daily_hw_cost, 2),
                'net_profit_usd_day': round(daily_profit, 2),
                'payback_days': round(specs['cost'] / daily_profit, 0) if daily_profit > 0 else None,
            }
    
    return card

def print_card(card):
    """Print a live card."""
    print(f"\n{'='*50}")
    print(f"{card['coin']} — Live Card")
    print(f"{'='*50}")
    print(f"Price: ${card['price_usd']:.8f}")
    print(f"Time:  {card['timestamp']}")
    print()
    
    for hw_name, hw in card['hardware'].items():
        print(f"  {hw_name} ({hw['algo']}):")
        print(f"    Hashrate:     {hw['hashrate']:,.0f} H/s")
        print(f"    Power:        {hw['power_watts']}W")
        print(f"    Cost:         ${hw['cost_usd']:,}")
        print(f"    Revenue/day:  ${hw['revenue_usd_day']:.2f}")
        print(f"    Electricity:  ${hw['electricity_usd_day']:.2f}/day")
        print(f"    HW amort:     ${hw['hw_amort_usd_day']:.2f}/day")
        print(f"    Net profit:   ${hw['net_profit_usd_day']:.2f}/day")
        if hw['payback_days']:
            print(f"    Payback:      {hw['payback_days']:.0f} days")
        else:
            print(f"    Payback:      Never")
        print()

def generate_all_cards():
    """Generate cards for all V1 chains."""
    print(f"\n{'='*60}")
    print(f"V1 Live Cards — {datetime.now()}")
    print(f"{'='*60}")
    
    # Load prices
    prices = {}
    for source in ['historical_data/external/external_data.json', 'historical_data/free_data.json']:
        filepath = os.path.join('/home/box/powpowpow', source)
        if os.path.exists(filepath):
            with open(filepath) as f:
                data = json.load(f)
            
            if 'prices' in data:
                for k, v in data['prices'].items():
                    if isinstance(v, dict):
                        prices[k.upper()] = v.get('usd', 0)
                    else:
                        prices[k.upper()] = v
            
            if 'coingecko' in data:
                for k, v in data['coingecko'].items():
                    if isinstance(v, dict) and 'usd' in v:
                        prices[k.upper()] = v['usd']
    
    # Generate cards
    cards = {}
    for chain in ['PRL', 'XMR', 'KAS', 'QUAN', 'CLORE', 'AKT', 'NOS', 'QUBIC']:
        price = prices.get(chain, 0)
        if price:
            card = generate_card(chain, price)
            cards[chain] = card
            print_card(card)
        else:
            print(f"\n{chain}: No price data")
    
    # Save all cards
    output_file = '/home/box/powpowpow/v1_live_cards.json'
    with open(output_file, 'w') as f:
        json.dump(cards, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    return cards

if __name__ == '__main__':
    generate_all_cards()
