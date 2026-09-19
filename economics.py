"""
Corrected Miner Economics
All formulas dimensionally coherent.
"""

import json
import os
from datetime import datetime, timezone
import sys

sys.path.insert(0, '/home/box/powpowpow')
from core import utcnow

# Hardware specs with NETWORK context
HARDWARE = {
    'PRL': {
        'H100': {'hashrate': 3000e12, 'power': 700, 'cost': 30000, 'algo': 'PearlHash'},
        'H200': {'hashrate': 4000e12, 'power': 700, 'cost': 40000, 'algo': 'PearlHash'},
        'RTX_4090': {'hashrate': 250e12, 'power': 450, 'cost': 2000, 'algo': 'PearlHash'},
        'network_hashrate': 21.9e18,  # Must provide network context
    },
    'XMR': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'RandomX'},
        'Ryzen_7_7800X3D': {'hashrate': 15000, 'power': 120, 'cost': 400, 'algo': 'RandomX'},
        'network_hashrate': 5.9e9,  # 5.9 GH/s
        'daily_emission': 432,  # XMR/day
    },
    'KAS': {
        'KS5_Pro': {'hashrate': 21e15, 'power': 3150, 'cost': 15000, 'algo': 'kHeavyHash'},
        'KS3_L': {'hashrate': 6e12, 'power': 3400, 'cost': 5000, 'algo': 'kHeavyHash'},
        'network_hashrate': None,  # Need to fetch
    },
    'QUAN': {
        'RTX_4090': {'hashrate': 1e9, 'power': 450, 'cost': 2000, 'algo': 'Poseidon2'},
        'network_hashrate': None,
    },
}

ELECTRICITY = 0.10
DEPRECIATION_YEARS = 3

def calculate_mining_revenue(chain, hw_name, price, network_hashrate=None, daily_emission=None):
    """
    CORRECT revenue formula:
    R_h = (h_machine / H_network) * E_network * P
    """
    if chain not in HARDWARE or hw_name not in HARDWARE[chain]:
        return None
    
    specs = HARDWARE[chain][hw_name]
    h_machine = specs['hashrate']
    
    # Get network context
    H_network = network_hashrate or HARDWARE[chain].get('network_hashrate')
    E_network = daily_emission or HARDWARE[chain].get('daily_emission')
    
    if not H_network or not E_network:
        return None  # Cannot calculate without network context
    
    # CORRECT: machine share × emission × price
    machine_share = h_machine / H_network
    daily_revenue = machine_share * E_network * price
    
    return {
        'machine_share': machine_share,
        'daily_revenue': daily_revenue,
        'hourly_revenue': daily_revenue / 24,
    }

def calculate_costs(hw_name, chain):
    """Calculate all costs for a hardware type."""
    if chain not in HARDWARE or hw_name not in HARDWARE[chain]:
        return None
    
    specs = HARDWARE[chain][hw_name]
    
    electricity = (specs['power'] / 1000) * 24 * ELECTRICITY
    hw_amort = specs['cost'] / (DEPRECIATION_YEARS * 365)
    
    return {
        'electricity_usd_day': electricity,
        'hw_amort_usd_day': hw_amort,
        'total_cost_usd_day': electricity + hw_amort,
    }

def calculate_mining_margin(chain, hw_name, price, network_hashrate=None, daily_emission=None):
    """
    CORRECT margin:
    Margin = (Revenue - Cost) / Revenue
    """
    rev = calculate_mining_revenue(chain, hw_name, price, network_hashrate, daily_emission)
    costs = calculate_costs(hw_name, chain)
    
    if not rev or not costs:
        return None
    
    net = rev['daily_revenue'] - costs['total_cost_usd_day']
    margin = net / rev['daily_revenue'] if rev['daily_revenue'] > 0 else 0
    
    return {
        'daily_revenue': rev['daily_revenue'],
        'daily_costs': costs['total_cost_usd_day'],
        'net_profit': net,
        'margin': margin,
        'machine_share': rev['machine_share'],
        'payback_days': specs['cost'] / net if net > 0 else None,
    }

def calculate_resource_premium(chain, hw_name, price, rental_price, network_hashrate=None, daily_emission=None):
    """
    Resource Premium = protocol_revenue_per_hour / external_rental_per_hour
    """
    rev = calculate_mining_revenue(chain, hw_name, price, network_hashrate, daily_emission)
    if not rev:
        return None
    
    hourly_protocol = rev['hourly_revenue']
    hourly_rental = rental_price
    
    premium = hourly_protocol / hourly_rental if hourly_rental > 0 else 0
    
    return {
        'protocol_revenue_per_hour': hourly_protocol,
        'external_rental_per_hour': hourly_rental,
        'resource_premium': premium,
        'interpretation': f'Protocol pays {premium:.1f}x external market' if premium > 1 else f'External market pays {1/premium:.1f}x protocol',
    }

def calculate_allocation_wedge(chain, hw_name, price, rental_price, network_hashrate=None, daily_emission=None):
    """
    Allocation Wedge = π_protocol - π_outside_option
    """
    rev = calculate_mining_revenue(chain, hw_name, price, network_hashrate, daily_emission)
    costs = calculate_costs(hw_name, chain)
    
    if not rev or not costs:
        return None
    
    # Protocol profit
    pi_protocol = rev['daily_revenue'] - costs['total_cost_usd_day']
    
    # Outside option profit (rental)
    pi_rental = rental_price * 24 - costs['electricity_usd_day']
    
    wedge = pi_protocol - pi_rental
    
    return {
        'pi_protocol': pi_protocol,
        'pi_rental': pi_rental,
        'allocation_wedge': wedge,
        'interpretation': 'Migrate TO protocol' if wedge > 0 else 'Migrate AWAY from protocol',
    }

def calculate_creation_pressure(emission_usd_hour, bid_depth_5pct):
    """
    Creation Pressure = emission per hour / 5% bid depth
    """
    if bid_depth_5pct <= 0:
        return None
    
    cp = emission_usd_hour / bid_depth_5pct
    return {
        'emission_usd_hour': emission_usd_hour,
        'bid_depth_5pct': bid_depth_5pct,
        'creation_pressure': cp,
        'interpretation': f'{cp:.1%} of 5% book created per hour',
    }

def calculate_absorption(aggressive_buy_usd, net_bid_addition_usd, aggressive_sell_usd, miner_exchange_usd, window_seconds=3600):
    """
    Absorption = (Buy + Net Bid Additions) / (Sell + Miner Exchange)
    All terms in same time window.
    """
    numerator = aggressive_buy_usd + net_bid_addition_usd
    denominator = aggressive_sell_usd + miner_exchange_usd
    
    if denominator <= 0:
        return None
    
    absorption = numerator / denominator
    
    return {
        'window_seconds': window_seconds,
        'aggressive_buy_usd': aggressive_buy_usd,
        'net_bid_addition_usd': net_bid_addition_usd,
        'aggressive_sell_usd': aggressive_sell_usd,
        'miner_exchange_usd': miner_exchange_usd,
        'absorption': absorption,
        'interpretation': 'Demand exceeds supply' if absorption > 1 else 'Supply exceeds demand',
    }

def build_live_card(chain, price, network_hashrate=None, daily_emission=None, rental_price=None):
    """Build corrected live card with all proper formulas."""
    card = {
        'chain': chain,
        'timestamp': utcnow(),
        'price_usd': price,
    }
    
    if chain in HARDWARE:
        for hw_name, specs in HARDWARE[chain].items():
            if hw_name == 'network_hashrate':
                continue
            
            # Revenue (correct formula)
            rev = calculate_mining_revenue(chain, hw_name, price, network_hashrate, daily_emission)
            costs = calculate_costs(hw_name, chain)
            
            if rev and costs:
                net = rev['daily_revenue'] - costs['total_cost_usd_day']
                margin = net / rev['daily_revenue'] if rev['daily_revenue'] > 0 else 0
                
                card[hw_name] = {
                    'hashrate': specs['hashrate'],
                    'power_watts': specs['power'],
                    'cost_usd': specs['cost'],
                    'algo': specs['algo'],
                    'machine_share': rev['machine_share'],
                    'revenue_usd_day': round(rev['daily_revenue'], 2),
                    'revenue_usd_hour': round(rev['hourly_revenue'], 4),
                    'electricity_usd_day': round(costs['electricity_usd_day'], 2),
                    'hw_amort_usd_day': round(costs['hw_amort_usd_day'], 2),
                    'total_cost_usd_day': round(costs['total_cost_usd_day'], 2),
                    'net_profit_usd_day': round(net, 2),
                    'margin': round(margin, 4),
                    'payback_days': round(specs['cost'] / net, 0) if net > 0 else None,
                }
                
                # Resource premium if rental price provided
                if rental_price:
                    rp = calculate_resource_premium(chain, hw_name, price, rental_price, network_hashrate, daily_emission)
                    if rp:
                        card[hw_name]['resource_premium'] = rp['resource_premium']
    
    return card

if __name__ == '__main__':
    # Test with XMR (we have network data)
    print("Testing corrected economics...")
    
    # XMR
    card = build_live_card('XMR', 564.59)
    print(f"\nXMR Card:")
    for hw, info in card.items():
        if isinstance(info, dict) and 'revenue_usd_day' in info:
            print(f"  {hw}:")
            print(f"    Machine share: {info['machine_share']:.8f}")
            print(f"    Revenue/day: ${info['revenue_usd_day']:.2f}")
            print(f"    Costs/day: ${info['total_cost_usd_day']:.2f}")
            print(f"    Net profit: ${info['net_profit_usd_day']:.2f}")
            print(f"    Margin: {info['margin']:.2%}")
    
    # Resource premium
    rp = calculate_resource_premium('XMR', 'Ryzen_9_7950X', 564.59, 0.02)
    print(f"\nResource Premium (vs $0.02/hr rental):")
    print(f"  Protocol: ${rp['protocol_revenue_per_hour']:.4f}/hr")
    print(f"  External: ${rp['external_rental_per_hour']:.4f}/hr")
    print(f"  Premium: {rp['resource_premium']:.1f}x")
    
    # Allocation wedge
    wedge = calculate_allocation_wedge('XMR', 'Ryzen_9_7950X', 564.59, 0.02)
    print(f"\nAllocation Wedge:")
    print(f"  Protocol profit: ${wedge['pi_protocol']:.2f}/day")
    print(f"  Rental profit: ${wedge['pi_rental']:.2f}/day")
    print(f"  Wedge: ${wedge['allocation_wedge']:.2f}/day")
    print(f"  {wedge['interpretation']}")
