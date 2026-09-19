"""
V1 Live Card Generator — network-share revenue model.

Revenue (mining):
    rig_coins_day = rig_hashrate / network_hashrate * daily_emission
    revenue_usd_day = rig_coins_day * price_usd

No magic yield_per_th / yield_per_h constants. Where network inputs are
missing the card returns no estimate with an explicit methodology flag
instead of a fabricated number. See TODO.md section 1.
"""

import json
import os
from datetime import datetime, timezone
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CALCULATION_VERSION = "2.0.0-network-share"

NETSTATE_FILE = os.path.join(BASE_DIR, 'chains', 'network_state.json')


def live_overrides():
    """Live chain-state overrides (chains/network_state.json). Returns {} if absent."""
    try:
        with open(NETSTATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

# ---------------------------------------------------------------------------
# Network state — seeded estimates with provenance. Replace with live
# collector values as pipes land. `None` means unknown: no revenue computed.
# ---------------------------------------------------------------------------
NETWORK = {
    'PRL': {
        'daily_emission': 500000.0,          # coins/day, chains/chain_fundamentals.json
        'network_hashrate': 21.9e18,         # H/s, prlscan 2026-09-18 (docs)
        'hashrate_source': 'prlscan 2026-09-18, re-measure via pearld',
        'emission_source': 'chain_fundamentals.json daily_emission',
        'as_of': '2026-09-18',
    },
    'XMR': {
        'daily_emission': 432.0,             # 0.6 XMR/block * 720 blocks/day (tail emission)
        'network_hashrate': 5.6e9,           # H/s, docs/minero 2026-09-18
        'hashrate_source': 'minero.cc/api + docs 2026-09-18, re-measure via monerod',
        'emission_source': 'tail emission 0.6 XMR x 720 blocks/day',
        'as_of': '2026-09-18',
    },
    # QUBIC is epoch/computor-based, not hashrate-proportional. Needs live
    # computor count + epoch emission from Qubic RPC before revenue is valid.
    'QUBIC': {'daily_emission': 1728000000.0, 'network_hashrate': None,
              'hashrate_source': None, 'emission_source': 'chain_fundamentals.json',
              'as_of': '2026-09-18',
              'needs': 'active_computors + epoch emission from rpc.qubic.org'},
    'QUAN': {'daily_emission': None, 'network_hashrate': None,
             'needs': 'emission schedule + network hashrate from Quantus telemetry'},
    # KAS gated: previous yield_per_th=50 priced one rig at $3.3B/day.
    # No KAS emission/hashrate in warehouse yet — no estimate until measured.
    'KAS': {'daily_emission': None, 'network_hashrate': None,
            'needs': 'kaspa emission + network hashrate, then re-enable',
            'gated': True, 'gate_reason': 'prior model produced $3.3B/day fiction'},
    'CLORE': {'model': 'rental'},
    'AKT': {'model': 'rental'},
    'NOS': {'model': 'rental'},
}

# Hardware registry — measured specs go here with source + date.
# hashrate in H/s, power in watts, cost in USD.
V1_HARDWARE = {
    'PRL': {
        'H100': {'hashrate': 3000e12, 'power': 700, 'cost': 30000, 'algo': 'PearlHash',
                 'spec_source': 'kryptex 2026-09, re-benchmark with pearl miner perf suite',
                 'spec_date': '2026-09-18'},
        'H200': {'hashrate': 4000e12, 'power': 700, 'cost': 40000, 'algo': 'PearlHash',
                 'spec_source': 'kryptex 2026-09, re-benchmark', 'spec_date': '2026-09-18'},
        'RTX_4090': {'hashrate': 250e12, 'power': 450, 'cost': 2000, 'algo': 'PearlHash',
                     'spec_source': 'kryptex 2026-09, re-benchmark', 'spec_date': '2026-09-18'},
    },
    'QUBIC': {
        'Ryzen_9_7950X': {'hashrate': None, 'power': 170, 'cost': 600, 'algo': 'Useful PoW',
                          'spec_source': 'placeholder, needs Qubic computor benchmark',
                          'spec_date': '2026-09-18'},
        'EPYC_7763': {'hashrate': None, 'power': 280, 'cost': 3000, 'algo': 'Useful PoW',
                      'spec_source': 'placeholder', 'spec_date': '2026-09-18'},
    },
    'XMR': {
        'Ryzen_9_7950X': {'hashrate': 22000, 'power': 170, 'cost': 600, 'algo': 'RandomX',
                          'spec_source': 'xmrig benchmark aggregate 2026-09, re-measure',
                          'spec_date': '2026-09-18'},
        'Ryzen_7_7800X3D': {'hashrate': 15000, 'power': 120, 'cost': 400, 'algo': 'RandomX',
                            'spec_source': 'xmrig benchmark aggregate 2026-09',
                            'spec_date': '2026-09-18'},
    },
    'KAS': {},  # gated, see NETWORK
    'QUAN': {
        'RTX_4090': {'hashrate': None, 'power': 450, 'cost': 2000, 'algo': 'Poseidon2',
                     'spec_source': 'placeholder, needs Quantus miner benchmark',
                     'spec_date': '2026-09-18'},
    },
    'CLORE': {
        'RTX_4090': {'hashrate': 0, 'power': 450, 'cost': 2000, 'algo': 'rental',
                     'rental_per_hour': 0.50, 'spec_source': 'clore.ai marketplace 2026-09-18',
                     'spec_date': '2026-09-18'},
    },
    'AKT': {
        'H100': {'hashrate': 0, 'power': 700, 'cost': 30000, 'algo': 'rental',
                 'rental_per_hour': 2.50, 'spec_source': 'akash marketplace sample 2026-09-18',
                 'spec_date': '2026-09-18'},
    },
    'NOS': {
        'H100': {'hashrate': 0, 'power': 700, 'cost': 30000, 'algo': 'inference',
                 'rental_per_hour': 2.00, 'spec_source': 'nosana markets sample 2026-09-18',
                 'spec_date': '2026-09-18'},
    },
}

DEPRECIATION_YEARS = 3


def _costs(power_w, cost_usd, electricity=0.10):
    daily_electricity = (power_w / 1000) * 24 * electricity
    daily_hw = cost_usd / (DEPRECIATION_YEARS * 365)
    return daily_electricity, daily_hw


def mining_revenue_usd_day(rig_hashrate, network_hashrate, daily_emission, price_usd):
    """Network-share revenue. Returns None when inputs missing."""
    if not rig_hashrate or not network_hashrate or not daily_emission or not price_usd:
        return None
    if network_hashrate <= 0 or price_usd <= 0:
        return None
    rig_coins = rig_hashrate / network_hashrate * daily_emission
    return rig_coins * price_usd


def live_state_block(symbol):
    """Latest STATE fundamentals for the card (04-spec fields).

    Returns issuance/depth/absorption/7d-change block. Pool->exchange stays
    null-disclosed until the miner graph exists. 7d changes need 8+ days of
    STATE; until then they report null with coverage note.
    """
    import glob
    rows = []
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'daily_state',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if (r.get('symbol') or '').upper() == symbol.upper():
                    rows.append(r)
    if not rows:
        return {'coverage': 'no STATE yet'}
    rows.sort(key=lambda r: (r.get('date', ''), r.get('venue', '')))
    by_date = {}
    for r in rows:
        d = by_date.setdefault(r.get('date'), {'bid': 0.0, 'mid': None,
                                               'spread': [], 'trades': 0})
        d['bid'] += r.get('bid_notional_20_mean') or 0
        if r.get('mid_close'):
            d['mid'] = r['mid_close']
        if r.get('spread_bps_median') is not None:
            d['spread'].append(r['spread_bps_median'])
        d['trades'] += r.get('n_trades') or 0
    dates = sorted(by_date)
    latest = by_date[dates[-1]]
    spread = sorted(latest['spread'])
    block = {
        'date': dates[-1],
        'days_of_state': len(dates),
        'bid_depth_top20_sum': round(latest['bid'], 2),
        'spread_bps_median': spread[len(spread) // 2] if spread else None,
        'trades_24h': latest['trades'],
        'pool_to_exchange_usd_day': None,
        'pool_to_exchange_method': 'unmeasured — needs pool/miner graph (pearld syncing)',
    }
    if len(dates) >= 8:
        first, last = by_date[dates[-8]], latest
        block['bid_depth_change_7d'] = (round((last['bid'] - first['bid']) / first['bid'], 4)
                                        if first['bid'] else None)
        block['mid_change_7d'] = (round((last['mid'] - first['mid']) / first['mid'], 4)
                                  if first['mid'] and last['mid'] else None)
    else:
        block['change_7d'] = f'insufficient history ({len(dates)}d STATE, need 8d)'
    return block


def generate_card(chain, price, network_data=None, electricity=0.10):
    """Generate a profitability card with methodology + assumptions stated."""
    if isinstance(price, dict):
        price = float(price.get('usd', 0) or 0)
    price = float(price or 0)

    net = dict(NETWORK.get(chain, {}))
    for live in (live_overrides().get(chain, {}),):
        if live.get('network_hashrate'):
            net['network_hashrate'] = live['network_hashrate']
            net['hashrate_source'] = live.get('hashrate_source', 'chains/network_state.json')
            net['as_of'] = live.get('as_of')
        if live.get('daily_emission_delta'):
            net['daily_emission'] = live['daily_emission_delta']
            net['emission_source'] = 'measured supply delta (chains/network_state.json)'
        elif live.get('daily_emission'):
            # engine-computed (e.g. Qubic epoch engine) beats static seeds
            net['daily_emission'] = live['daily_emission']
            net['emission_source'] = live.get(
                'emission_source', 'chains/network_state.json')
            net['as_of'] = live.get('as_of', net.get('as_of'))
    if network_data:
        # live overrides (collector-provided); explicit wins over seed
        for k in ('daily_emission', 'network_hashrate'):
            if network_data.get(k):
                net[k] = network_data[k]
                net[f'{k}_source'] = network_data.get(f'{k}_source', 'live collector')

    card = {
        'coin': chain,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'price_usd': price,
        'calculation_version': CALCULATION_VERSION,
        'methodology': 'rig_hashrate / network_hashrate * daily_emission * price',
        'electricity_usd_kwh': electricity,
        'network': {k: net.get(k) for k in
                    ('daily_emission', 'network_hashrate', 'hashrate_source',
                     'emission_source', 'as_of', 'needs', 'gated', 'gate_reason')},
        'fundamentals': None,  # filled below; None only if no STATE yet
        'hardware': {},
    }
    try:
        fb = live_state_block(chain)
        em = net.get('daily_emission')
        fb['miner_issuance_usd_day'] = round(em * price, 2) if em and price else None
        bid = fb.get('bid_depth_top20_sum') or 0
        fb['required_absorption_usd_day'] = fb['miner_issuance_usd_day']
        fb['absorption_burden'] = (round(fb['miner_issuance_usd_day'] / bid, 3)
                                   if fb['miner_issuance_usd_day'] and bid > 0 else None)
        card['fundamentals'] = fb
    except Exception as e:
        card['fundamentals'] = {'error': f'state read failed: {str(e)[:100]}'}

    if net.get('gated'):
        card['status'] = 'gated'
        card['gate_reason'] = net.get('gate_reason')
        return card

    for hw_name, specs in V1_HARDWARE.get(chain, {}).items():
        daily_elec, daily_hw = _costs(specs['power'], specs['cost'], electricity)
        algo = specs.get('algo')
        revenue = None
        assumption = None
        if algo in ('rental', 'inference'):
            revenue = specs.get('rental_per_hour', 0) * 24
            assumption = 'assumes 100% utilization at quoted ask, 24h; before platform fees'
        else:
            revenue = mining_revenue_usd_day(
                specs.get('hashrate'), net.get('network_hashrate'),
                net.get('daily_emission'), price)
            if revenue is None:
                missing = [k for k in ('rig_hashrate', 'network_hashrate', 'daily_emission', 'price')
                           if not {'rig_hashrate': specs.get('hashrate'),
                                   'network_hashrate': net.get('network_hashrate'),
                                   'daily_emission': net.get('daily_emission'),
                                   'price': price}[k]]
                assumption = f'no estimate — missing: {", ".join(missing)}'
        profit = revenue - daily_elec - daily_hw if revenue is not None else None
        card['hardware'][hw_name] = {
            'hashrate': specs.get('hashrate'),
            'power_watts': specs['power'],
            'cost_usd': specs['cost'],
            'algo': algo,
            'spec_source': specs.get('spec_source'),
            'spec_date': specs.get('spec_date'),
            'revenue_usd_day': round(revenue, 2) if revenue is not None else None,
            'electricity_usd_day': round(daily_elec, 2),
            'hw_amort_usd_day': round(daily_hw, 2),
            'net_profit_usd_day': round(profit, 2) if profit is not None else None,
            'payback_days': round(specs['cost'] / profit, 0) if profit and profit > 0 else None,
            'assumption': assumption,
        }
    return card


def print_card(card):
    print(f"\n{'='*50}")
    print(f"{card['coin']} — Live Card ({card.get('calculation_version')})")
    print(f"{'='*50}")
    print(f"Price: ${card['price_usd']:.8f}")
    print(f"Time:  {card['timestamp']}")
    if card.get('status') == 'gated':
        print(f"GATED: {card.get('gate_reason')}")
        return
    net = card.get('network', {})
    print(f"Network: emission={net.get('daily_emission')}/day "
          f"hashrate={net.get('network_hashrate')} ({net.get('hashrate_source')})")
    print()
    for hw_name, hw in card['hardware'].items():
        print(f"  {hw_name} ({hw['algo']}):")
        if hw['revenue_usd_day'] is None:
            print(f"    Revenue/day:  NO ESTIMATE")
            print(f"    Reason:       {hw['assumption']}")
        else:
            print(f"    Revenue/day:  ${hw['revenue_usd_day']:.2f}")
        print(f"    Electricity:  ${hw['electricity_usd_day']:.2f}/day")
        print(f"    HW amort:     ${hw['hw_amort_usd_day']:.2f}/day")
        np_ = hw['net_profit_usd_day']
        print(f"    Net profit:   ${np_:.2f}/day" if np_ is not None else "    Net profit:   NO ESTIMATE")
        print(f"    Payback:      {hw['payback_days']:.0f} days" if hw['payback_days'] else "    Payback:      Never / N/A")
        if hw.get('assumption'):
            print(f"    Note:         {hw['assumption']}")
        print()


def generate_all_cards(electricity=0.10):
    print(f"\n{'='*60}")
    print(f"V1 Live Cards ({CALCULATION_VERSION}) — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")
    prices = {}
    for source in ['historical_data/external/external_data.json', 'historical_data/free_data.json']:
        filepath = os.path.join(BASE_DIR, source)
        if os.path.exists(filepath):
            with open(filepath) as f:
                data = json.load(f)
            if 'prices' in data:
                for k, v in data['prices'].items():
                    prices[k.upper()] = v.get('usd', 0) if isinstance(v, dict) else v
            if 'coingecko' in data:
                for k, v in data['coingecko'].items():
                    if isinstance(v, dict) and 'usd' in v:
                        prices[k.upper()] = v['usd']
    cards = {}
    for chain in ['PRL', 'XMR', 'KAS', 'QUAN', 'CLORE', 'AKT', 'NOS', 'QUBIC']:
        price = prices.get(chain, 0)
        if price:
            card = generate_card(chain, price, electricity=electricity)
            cards[chain] = card
            print_card(card)
        else:
            print(f"\n{chain}: No price data")
    output_file = os.path.join(BASE_DIR, 'v1_live_cards.json')
    with open(output_file, 'w') as f:
        json.dump(cards, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    return cards


if __name__ == '__main__':
    generate_all_cards()
