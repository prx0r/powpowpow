"""
Miner Economics Calculator — network-share model with stated assumptions.

Revenue per rig:
    rig_hashrate / network_hashrate * daily_emission * price

Sell pressure uses a disclosed per-coin methodology until miner-flow
measurement exists (see SELL_METHODOLOGY). Nothing here is presented as
measured miner behavior.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CHAINS_DIR = os.path.join(BASE_DIR, 'chains')
ECONOMICS_DIR = os.path.join(CHAINS_DIR, 'economics')
os.makedirs(ECONOMICS_DIR, exist_ok=True)

CALCULATION_VERSION = "2.0.0-network-share"


def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


FUNDAMENTALS = load_json('chain_fundamentals.json')
MINER_REVENUE = load_json('miner_revenue.json')

# Seeded network state (same provenance as v1_live_cards). Live collectors
# should override via network_data param.
NETWORK = {
    'XMR': {'daily_emission': 432.0, 'network_hashrate': 5.6e9,
            'hashrate_source': 'minero.cc/docs 2026-09-18', 'as_of': '2026-09-18'},
    'PRL': {'daily_emission': 500000.0, 'network_hashrate': 21.9e18,
            'hashrate_source': 'prlscan 2026-09-18', 'as_of': '2026-09-18'},
}

# Hardware registry with provenance. hashrate H/s, power W, cost USD.
HARDWARE_SPECS = {
    'XMR': {
        'RandomX': {
            'cpu': {'hashrate': 20000, 'power': 100, 'cost': 500,
                    'spec_source': 'xmrig aggregate 2026-09-18', 'spec_date': '2026-09-18'},
            'high_end_cpu': {'hashrate': 100000, 'power': 200, 'cost': 2000,
                             'spec_source': 'xmrig aggregate 2026-09-18', 'spec_date': '2026-09-18'},
        }
    },
    'PRL': {
        'PearlHash': {
            'rtx_4080': {'hashrate': 203e12, 'power': 270, 'cost': 1250,
                         'spec_source': 'kryptex 2026-09-18', 'spec_date': '2026-09-18'},
            'cmp_170hx': {'hashrate': 175e12, 'power': 240, 'cost': 4000,
                          'spec_source': 'kryptex 2026-09-18', 'spec_date': '2026-09-18'},
        }
    },
}

# Sell methodology per coin — assumption until pool→miner→exchange flow exists.
SELL_METHODOLOGY = {
    '_default': {'sell_fraction': 0.6, 'method': 'assumed constant; replace with miner-flow measurement',
                 'confidence': 'low'},
}

DEFAULT_ELECTRICITY = 0.10


def rig_revenue_usd_day(rig_hashrate, network_hashrate, daily_emission, price):
    if not rig_hashrate or not network_hashrate or not daily_emission or not price:
        return None
    if network_hashrate <= 0 or price <= 0:
        return None
    return rig_hashrate / network_hashrate * daily_emission * price


def calculate_miner_economics(symbol, electricity=DEFAULT_ELECTRICITY, network_data=None):
    """Calculate miner economics with methodology + assumptions on output."""
    fund = FUNDAMENTALS.get(symbol, {})
    revenue = MINER_REVENUE.get(symbol, {})
    net = dict(NETWORK.get(symbol, {}))
    if network_data:
        net.update({k: v for k, v in network_data.items() if v is not None})

    daily_emission = fund.get('daily_emission', 0) or net.get('daily_emission', 0) or 0
    price = revenue.get('price', 0) or 0
    daily_emission_usd = daily_emission * price if daily_emission and price else 0

    sell_meta = SELL_METHODOLOGY.get(symbol, SELL_METHODOLOGY['_default'])
    sell_fraction = sell_meta['sell_fraction']
    daily_sell_pressure = daily_emission_usd * sell_fraction if daily_emission_usd else 0

    hardware_profitability = {}
    if symbol in HARDWARE_SPECS:
        for algo, devices in HARDWARE_SPECS[symbol].items():
            for device, specs in devices.items():
                rev = rig_revenue_usd_day(specs['hashrate'], net.get('network_hashrate'),
                                          daily_emission, price)
                elec = (specs['power'] / 1000) * 24 * electricity
                profit = rev - elec if rev is not None else None
                hardware_profitability[device] = {
                    'hashrate': specs['hashrate'],
                    'power_w': specs['power'],
                    'cost_usd': specs['cost'],
                    'spec_source': specs.get('spec_source'),
                    'spec_date': specs.get('spec_date'),
                    'network_hashrate': net.get('network_hashrate'),
                    'network_hashrate_source': net.get('hashrate_source'),
                    'daily_revenue_usd': round(rev, 2) if rev is not None else None,
                    'daily_electricity_usd': round(elec, 2),
                    'daily_profit_usd': round(profit, 2) if profit is not None else None,
                    'revenue_method': 'rig/network * emission * price' if rev is not None
                    else 'no estimate — missing network hashrate, emission, or price',
                    'payback_days': specs['cost'] / profit if profit and profit > 0 else None,
                    'annual_roi': (profit * 365 / specs['cost'] * 100) if profit and specs['cost'] > 0 else None,
                }

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'calculation_version': CALCULATION_VERSION,
        'symbol': symbol,
        'name': fund.get('name'),
        'daily_emission': daily_emission,
        'daily_emission_usd': daily_emission_usd,
        'annual_emission_usd': daily_emission_usd * 365 if daily_emission_usd else 0,
        'sell_fraction': sell_fraction,
        'sell_methodology': sell_meta['method'],
        'sell_confidence': sell_meta['confidence'],
        'daily_sell_pressure_usd': daily_sell_pressure,
        'annual_sell_pressure_usd': daily_sell_pressure * 365 if daily_sell_pressure else 0,
        'volume_24h': revenue.get('volume_24h', 0),
        'absorption_ratio': revenue.get('volume_24h', 0) / daily_emission_usd if daily_emission_usd > 0 else None,
        'market_cap': revenue.get('market_cap', 0),
        'dilution_pressure': revenue.get('miner_burden', {}).get('dilution_pressure'),
        'hardware_profitability': hardware_profitability,
        'electricity_cost_kwh': electricity,
    }


def calculate_all(electricity=DEFAULT_ELECTRICITY):
    print(f"\n{'='*60}")
    print(f"Calculating Miner Economics ({CALCULATION_VERSION}) — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")
    all_economics = {}
    for symbol in FUNDAMENTALS:
        print(f"\n[{symbol}]")
        try:
            economics = calculate_miner_economics(symbol, electricity=electricity)
            all_economics[symbol] = economics
            print(f"  Daily emission: ${economics['daily_emission_usd']:,.0f}")
            print(f"  Daily sell pressure ({economics['sell_methodology'][:40]}...): "
                  f"${economics['daily_sell_pressure_usd']:,.0f}")
            print(f"  Absorption: {economics['absorption_ratio']:.1f}x" if economics['absorption_ratio'] else "  Absorption: N/A")
            if economics['hardware_profitability']:
                print("  Hardware profitability:")
                for device, prof in economics['hardware_profitability'].items():
                    if prof['daily_profit_usd'] is None:
                        print(f"    {device}: NO ESTIMATE ({prof['revenue_method']})")
                    elif prof['payback_days']:
                        print(f"    {device}: ${prof['daily_profit_usd']:.2f}/day, {prof['payback_days']:.0f} days payback")
                    else:
                        print(f"    {device}: ${prof['daily_profit_usd']:.2f}/day")
        except Exception as e:
            print(f"  Error: {e}")
    output_file = os.path.join(ECONOMICS_DIR, 'miner_economics.json')
    with open(output_file, 'w') as f:
        json.dump(all_economics, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    return all_economics


if __name__ == '__main__':
    calculate_all()
