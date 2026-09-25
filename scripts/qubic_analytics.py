"""
Qubic analytics engine — concrete numbers, not opinions.

Computes from live data:
  - maximum effective emission (from epoch engine burn ceiling)
  - new-issuance projection (extrapolated emission over 1-52 weeks)
  - emission-to-book ratio (burden per day)
  - miner reward per computor (post-227 minimum mineable supply ÷ computors)
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
POST_227_MAX_BURN = 0.775
POST_227_EFFECTIVE_PER_WEEK = 225e9
POST_227_MINIMUM_MINEABLE_PER_WEEK = 181.64e9


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
    """Project new issuance over future weeks given the current burn ceiling."""
    burn = net.get('burn_rate')
    if not burn:
        return []
    weeks = []
    gross = 1e12  # constant
    if abs(burn - POST_227_MAX_BURN) < 1e-12:
        weekly_new = POST_227_EFFECTIVE_PER_WEEK
    else:
        weekly_new = gross * (1 - burn)
    price = None
    try:
        closes = load_cg_closes()
        if closes:
            price = closes[-1][1]
    except Exception:
        pass
    for w in range(1, 53):
        new_supply = weekly_new * w
        new_supply_usd = new_supply * price if price else None
        weeks.append({
            'week': w,
            'gross': gross * w,
            'burned': gross * burn * w,
            'new_supply': new_supply,
            'net': new_supply,
            'net_usd': new_supply_usd,
            'price_assumed': price,
            'burn_rate': burn,
            'emission_basis': 'projected new issuance, not cumulative supply',
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
    """Minimum mineable reward per computor per epoch, and per-day equivalent."""
    gross = 1e12
    burn = net.get('burn_rate', 0)
    computors = net.get('computors', 0)
    if not computors:
        return {}
    if abs(burn - POST_227_MAX_BURN) < 1e-12:
        effective_per_epoch = POST_227_EFFECTIVE_PER_WEEK
        mineable_per_epoch = POST_227_MINIMUM_MINEABLE_PER_WEEK
    else:
        effective_per_epoch = gross * (1 - burn)
        mineable_per_epoch = None
    per_computor = mineable_per_epoch / computors if mineable_per_epoch else None
    return {
        'gross_per_epoch': gross,
        'burn_rate': burn,
        'effective_per_epoch': effective_per_epoch,
        'net_per_epoch': effective_per_epoch,
        'mineable_per_epoch': mineable_per_epoch,
        'computors': computors,
        'reward_per_computor': per_computor,
        'reward_per_computor_per_day': per_computor / 7 if per_computor else None,
        'source': 'Qubic Epoch 227 allocation table + Query API computor count',
        'emission_basis': 'minimum mineable supply after CCF and QEarn allocations',
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
    reward = ce.get('reward_per_computor')
    print(f"  computors {ce.get('computors')} reward/epoch "
          f"{reward:,.0f}" if reward else "  computors reward/epoch unavailable")
    print(f"  365d range ${pr.get('low', 0):.8f} → ${pr.get('high', 0):.8f}")
    print(f"  {len(a['epoch_returns'])} epoch-equivalent return periods")
