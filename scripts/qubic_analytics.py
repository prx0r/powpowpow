"""
Qubic analytics engine — concrete numbers, not opinions.

Computes from live data:
  - net emission (from epoch engine burn schedule)
  - supply projection (extrapolated emission over 1-52 weeks)
  - emission-to-book ratio (burden per day)
  - miner reward per computor (1T gross / 676 computors × burn share)
  - epoch return series (from CG closes)
  - demand per epoch (tx volume per epoch tick range)

Every number carries its source and version.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402

NETSTATE_FILE = os.path.join(BASE_DIR, 'chains', 'network_state.json')
EPOCH_STATE_FILE = os.path.join(BASE_DIR, 'warehouse', 'qubic_epoch_state.json')


def load_netstate():
    try:
        return json.load(open(NETSTATE_FILE))
    except (OSError, ValueError):
        return {}


def load_cg_closes(sym='QUBIC'):
    closes = []
    import glob
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'price_history',
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


def load_daily_state(symbol='QUBIC'):
    rows = []
    import glob
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'daily_state',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    if (r.get('symbol') or '').upper() == symbol:
                        rows.append(r)
                except ValueError:
                    pass
    rows.sort(key=lambda r: r.get('date', ''))
    return rows


def load_demand_snapshots():
    rows = []
    import glob
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'network_demand',
            'chain=qubic', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    rows.sort(key=lambda r: r.get('observed_at', ''))
    return rows


def supply_curve(net):
    """Project total supply over future weeks given current burn rate."""
    if not net.get('burn_rate'):
        return []
    weeks = []
    gross = 1e12  # constant
    burn = net['burn_rate']
    daily = gross * (1 - burn) / 7
    cumulative_supply = net.get('total_transactions', 0)  # proxy for existing supply proxy
    price = None
    try:
        closes = load_cg_closes()
        if closes:
            price = closes[-1][1]
    except Exception:
        pass
    for w in range(1, 53):
        net_new = gross * (1 - burn) * w
        net_usd = net_new * price if price else None
        weeks.append({
            'week': w,
            'gross': gross * w,
            'burned': gross * burn * w,
            'net': net_new,
            'net_usd': net_usd,
            'price_assumed': price,
        })
    return weeks


def epoch_returns(closes):
    """7-day returns aligned to epoch boundaries (weekdays approximation)."""
    if len(closes) < 14:
        return []
    returns = []
    n = len(closes)
    if n < 8:
        return []
    # Trailing 7d returns, most recent first
    for end in range(n - 1, 6, -7):
        start = max(0, end - 7)
        a_date, a_price = closes[start]
        b_date, b_price = closes[end]
        if a_price and b_price and a_price > 0:
            returns.append({
                'from': a_date, 'to': b_date,
                'return_pct': round((b_price - a_price) / a_price * 100, 2),
                'price_from': a_price, 'price_to': b_price,
            })
    return returns


def emission_valuation(net):
    """Current emission valued at price, relative to book depth and volume."""
    try:
        closes = load_cg_closes()
        price = closes[-1][1] if closes else None
    except Exception:
        price = None
    daily_emission = net.get('daily_emission')
    states = load_daily_state()
    latest = states[-1] if states else {}
    bid_depth = latest.get('bid_notional_20_mean')
    volume = latest.get('trade_notional_sum')
    if not daily_emission:
        return {'error': 'no emission data'}
    emission_usd = daily_emission * price if price else None
    return {
        'price': price,
        'daily_emission': daily_emission,
        'daily_emission_usd': emission_usd,
        'bid_depth': bid_depth,
        'burden_vs_book': round(emission_usd / bid_depth, 2) if emission_usd and bid_depth else None,
        'volume': volume,
        'issuance_to_volume': round(emission_usd / volume, 2) if emission_usd and volume else None,
        'source': 'epoch engine + CG closes + venue daily_state',
    }


def computor_economics(net):
    """Reward per computor per epoch, and per-day equivalent."""
    gross = 1e12
    burn = net.get('burn_rate', 0)
    computors = net.get('computors', 0)
    if not computors:
        return {}
    net_per_epoch = gross * (1 - burn)
    per_computor = net_per_epoch / computors
    return {
        'gross_per_epoch': gross,
        'burn_rate': burn,
        'net_per_epoch': net_per_epoch,
        'computors': computors,
        'reward_per_computor': per_computor,
        'reward_per_computor_per_day': per_computor / 7,
        'source': 'epoch engine + Query API computor count',
    }


def build_qubic_analytics():
    """Full Qubic analytics bundle — the first complete example."""
    net = load_netstate().get('QUBIC', {})
    closes = load_cg_closes()
    state = load_daily_state()
    demand = load_demand_snapshots()

    # Epoch return series
    er = epoch_returns(closes)

    # 52-week price range
    prices = [c[1] for c in closes if c[1]]
    price_range = {
        'high': max(prices) if prices else None,
        'low': min(prices) if prices else None,
        'current': prices[-1] if prices else None,
        'high_date': closes[prices.index(max(prices))][0] if prices else None,
        'low_date': closes[prices.index(min(prices))][0] if prices else None,
    }

    # Demand deltas
    demand_deltas = {}
    if len(demand) >= 2:
        a, b = demand[-2], demand[-1]
        for k in ('total_transactions', 'total_transfers', 'total_volume'):
            av, bv = a.get(k), b.get(k)
            if av is not None and bv is not None and av > 0:
                demand_deltas[k] = {'delta': bv - av, 'pct': round((bv - av) / av * 100, 2)}

    analytics = {
        'symbol': 'QUBIC',
        'computed_at': utcnow(),
        'emission': emission_valuation(net),
        'supply_curve': supply_curve(net),
        'epoch_returns': er,
        'price_range_365d': price_range,
        'computor_economics': computor_economics(net),
        'network': {
            'epoch': net.get('epoch'),
            'epoch_progress': net.get('epoch_progress'),
            'tick_rate': net.get('tick_rate'),
            'ticks_per_epoch': net.get('ticks_per_epoch'),
            'burn_rate': net.get('burn_rate'),
            'daily_emission': net.get('daily_emission'),
            'total_transactions': net.get('total_transactions'),
            'total_transfers': net.get('total_transfers'),
            'total_volume': net.get('total_volume'),
            'computors': net.get('computors'),
            'doge_tasks': net.get('doge_tasks'),
        },
        'demand_deltas': demand_deltas,
        'state': state[-6:] if state else [],
    }

    out = os.path.join(BASE_DIR, 'warehouse', 'qubic_analytics.json')
    with open(out, 'w') as f:
        json.dump(analytics, f, indent=2, default=str)
    print(f"[QUBIC ANALYTICS] saved to {out}")
    return analytics


if __name__ == '__main__':
    a = build_qubic_analytics()
    em_usd = a['emission'].get('daily_emission_usd')
    burden = a['emission'].get('burden_vs_book')
    ce = a['computor_economics']
    pr = a['price_range_365d']
    print(f"  emission ${em_usd:,.0f}/day")
    print(f"  burden {burden}x")
    print(f"  computors {ce.get('computors')} reward/epoch {ce.get('reward_per_computor'):,.0f}")
    print(f"  365d range ${pr.get('low', 0):.8f} → ${pr.get('high', 0):.8f}")
    print(f"  {len(a['epoch_returns'])} epoch-equivalent return periods")
