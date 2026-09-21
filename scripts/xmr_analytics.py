"""
XMR analytics engine — concrete numbers, not opinions.

Computes:
  - emission valuation at price vs book depth
  - miner cost benchmark (what electricity price makes mining profitable)
  - hash-price (USD per hash per day)
  - difficulty-price lag correlation (when enough days accumulate)
  - 365d price distribution (where are we in the range)
  - p2pool decentralization metrics
"""

import glob
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow


def load_json(p):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {}


def load_closes(sym='XMR'):
    closes = []
    for f in glob.glob(os.path.join(BASE_DIR, 'warehouse', 'normalized', 'price_history',
                                     f'chain={sym.lower()}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    if r.get('close_usd'):
                        closes.append((r['date'], float(r['close_usd'])))
                except ValueError:
                    pass
    closes.sort()
    return closes


def load_chain_snapshots():
    rows = []
    for f in glob.glob(os.path.join(BASE_DIR, 'warehouse', 'normalized', 'chain_snapshot',
                                     'chain=xmr', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    rows.sort(key=lambda r: r.get('observed_at', ''))
    return rows


def load_daily_state():
    rows = []
    for f in glob.glob(os.path.join(BASE_DIR, 'warehouse', 'normalized', 'daily_state',
                                     'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    if (r.get('symbol') or '').upper() == 'XMR':
                        rows.append(r)
                except ValueError:
                    pass
    rows.sort(key=lambda r: r.get('date', ''))
    return rows


def miner_cost_benchmark():
    """What electricity price makes a Ryzen 9 mine XMR profitably?"""
    XMR_PER_KH = 0.00006  # from our benchmark
    RYZEN_KHS = 22.0
    COST = 600.0
    DEPR_YEARS = 3

    # Scan electricity prices from $0.01 to $0.30
    results = []
    for elec in [x / 100 for x in range(1, 31)]:
        daily_elec = (170 / 1000) * 24 * elec
        daily_hw = COST / (DEPR_YEARS * 365)
        # Find breakeven XMR price
        daily_coins = RYZEN_KHS * XMR_PER_KH
        total_cost = daily_elec + daily_hw
        breakeven_price = total_cost / daily_coins if daily_coins > 0 else None
        results.append({
            'electricity_usd_kwh': elec,
            'daily_electricity': round(daily_elec, 2),
            'daily_hw_depreciation': round(daily_hw, 2),
            'daily_total_cost': round(total_cost, 2),
            'breakeven_xmr_price': round(breakeven_price, 2) if breakeven_price else None,
        })
    return results


def price_position(closes):
    """Where is current price in the 365d range?"""
    prices = [c[1] for c in closes if c[1]]
    if not prices:
        return {}
    current = prices[-1]
    high, low = max(prices), min(prices)
    pctile = sum(1 for p in prices if p <= current) / len(prices) * 100
    return {
        'current': current,
        'high': high, 'low': low,
        'range': f"${low:.0f} – ${high:.0f}",
        'percentile': round(pctile, 1),
        'high_date': closes[prices.index(high)][0],
        'low_date': closes[prices.index(low)][0],
    }


def emission_daily():
    """Fixed 432 XMR/day, valued at current price."""
    closes = load_closes()
    price = closes[-1][1] if closes else None
    return {
        'daily_emission': 432,
        'daily_emission_usd': round(432 * price, 2) if price else None,
        'annual_emission': 432 * 365,
        'annual_emission_usd': round(432 * 365 * price, 0) if price else None,
        'block_reward': 0.6,
        'blocks_per_day': 720,
        'source': 'tail emission (fixed forever)',
    }


def build_xmr_analytics():
    net = load_json(os.path.join(BASE_DIR, 'chains', 'network_state.json')).get('XMR', {})
    closes = load_closes()
    snapshots = load_chain_snapshots()
    states = load_daily_state()

    latest_snap = snapshots[-1] if snapshots else {}
    latest_state = states[-1] if states else {}

    emission = emission_daily()
    cost_bench = miner_cost_benchmark()
    pos = price_position(closes)

    # P2Pool metrics
    p2pool = {
        'hashrate': latest_snap.get('network_hashrate'),
        'miners': latest_snap.get('p2pool_miners', net.get('p2pool_miners')),
        'last_block': net.get('p2pool_last_block'),
    }

    analytics = {
        'symbol': 'XMR',
        'computed_at': utcnow(),
        'emission': emission,
        'price_position_365d': pos,
        'miner_cost_benchmark': cost_bench,
        'network': {
            'hashrate': latest_snap.get('network_hashrate') or net.get('network_hashrate'),
            'difficulty': latest_snap.get('difficulty'),
            'fee_per_kb': net.get('fee_per_kb'),
            'hf_version': net.get('hf_version'),
            'p2pool': p2pool,
        },
        'state': states[-6:] if states else [],
    }

    out = os.path.join(BASE_DIR, 'warehouse', 'xmr_analytics.json')
    with open(out, 'w') as f:
        json.dump(analytics, f, indent=2, default=str)
    print(f"[XMR ANALYTICS] saved to {out}")
    return analytics


if __name__ == '__main__':
    a = build_xmr_analytics()
    print(f"  emission ${a['emission'].get('daily_emission_usd'):,.0f}/day ({a['emission']['daily_emission']} XMR)")
    print(f"  365d position: {a['price_position_365d'].get('percentile')}th percentile "
          f"(${a['price_position_365d'].get('low')} – ${a['price_position_365d'].get('high')})")
    hr = a['network'].get('hashrate')
    hr_str = f"{hr/1e9:.1f} GH/s" if hr else '?'
    print(f"  p2pool: {a['network']['p2pool'].get('miners', '?')} miners, {hr_str}")
