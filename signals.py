"""
Canonical signals v1 — derived measurements with provenance, versioned.

Vision rule: a signal is a graph transformation with provenance, not an
LLM opinion. Every signal carries asset, direction, strength, drivers,
evidence (record IDs), assumptions, confidence, definition version, and
timestamp. Transformations are versioned (miner_pressure_v1 vs v2) and
rerun against immutable history — never overwritten.

miner_pressure_v1 inputs (all measured except where flagged):
  creation burden  = daily emission USD / cross-venue bid notional
  depth thinness   = 1 / total bid notional (relative, cross-sectional)
  illiquidity      = median spread_bps (relative, cross-sectional)
Unmeasured (assumed, disclosed): miner sell fraction / exchange-bound
flow. v1 does NOT pretend to know realization — it scores structural
creation burden vs absorbable liquidity.

Direction comes from the cross-sectional z-score of the burden composite:
coins bearing unusually large fresh-supply-vs-book burdens score bearish.
Strength = logistic(|z|). With <4 markets of data the module refuses
(insufficient cross-section) rather than fabricating.

Usage:
    python3 signals.py --date 2026-09-19
"""

import argparse
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import store_normalized  # noqa: E402

SIGNAL_VERSION = "miner_pressure_v1"
CALCULATION_VERSION = "signals-v1.0"


def read_states(date, chain='venue'):
    rows = []
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'daily_state',
            f'chain={chain}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get('date') == date:
                    rows.append(r)
    return rows


def load_emission(symbol):
    """Daily native emission + price lookup. Returns (emission, price, sources)."""
    try:
        fund = json.load(open(os.path.join(BASE_DIR, 'chains', 'chain_fundamentals.json')))
    except OSError:
        fund = {}
    e = (fund.get(symbol, {}) or {}).get('daily_emission')
    if e:
        return e, f"chain_fundamentals.json:{symbol}.daily_emission"
    try:
        from emission import estimate as emission_estimate
        est, prov = emission_estimate(symbol)
        if est:
            return est, f"emission.py:{symbol} ({prov.get('source', '')} [{prov.get('confidence', '')}])"
    except Exception:
        pass
    return None, "unknown"


def zscore(xs):
    n = len(xs)
    if n < 2:
        return [0.0] * n
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    sd = math.sqrt(var) or 1e-12
    return [(x - m) / sd for x in xs]


def logistic(x):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def build_signals(date):
    states = read_states(date) + read_states(date, 'safetrade')
    # Aggregate cross-venue per symbol: sum depths, volume-weighted spread,
    # latest close as price proxy.
    agg = {}
    for s in states:
        sym = (s.get('symbol') or '').upper()
        a = agg.setdefault(sym, {'bid': 0.0, 'ask': 0.0, 'spreads': [],
                                 'closes': [], 'states': [], 'trades_n': 0})
        if s.get('bid_notional_20_mean'):
            a['bid'] += s['bid_notional_20_mean']
        if s.get('ask_notional_20_mean'):
            a['ask'] += s['ask_notional_20_mean']
        if s.get('spread_bps_median') is not None:
            a['spreads'].append(s['spread_bps_median'])
        if s.get('mid_close'):
            a['closes'].append(s['mid_close'])
        a['states'].append(s.get('record_id'))
        a['trades_n'] += s.get('n_trades', 0) or 0

    # Measured burden per symbol (needs emission + price + depth).
    scored = []
    for sym, a in agg.items():
        emission, emission_src = load_emission(sym)
        price = a['closes'][-1] if a['closes'] else None
        if not emission or not price or a['bid'] <= 0:
            continue
        emission_usd = emission * price
        burden = emission_usd / a['bid']  # days of book to absorb one day of supply
        spread_med = sorted(a['spreads'])[len(a['spreads']) // 2] if a['spreads'] else None
        scored.append({'symbol': sym, 'burden': burden,
                       'emission_usd': emission_usd, 'bid': a['bid'],
                       'spread_med': spread_med, 'states': a['states'],
                       'emission_src': emission_src, 'trades_n': a['trades_n']})

    if len(scored) < 4:
        print(f"[SIGNALS {date}] insufficient cross-section ({len(scored)} markets) — refusing")
        return []

    zs = zscore([math.log10(max(s['burden'], 1e-12)) for s in scored])
    out = []
    for s, z in zip(scored, zs):
        direction = 'bearish' if z > 0.5 else ('bullish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        drivers = [
            f"emission_usd_day={s['emission_usd']:,.0f}",
            f"bid_notional_20_sum={s['bid']:,.0f}",
            f"burden={s['burden']:.2f}x",
        ]
        if s['spread_med'] is not None:
            drivers.append(f"spread_bps_med={s['spread_med']:.1f}")
        sig = {
            'asset': s['symbol'],
            'signal': 'miner_pressure',
            'version': SIGNAL_VERSION,
            'calculation_version': CALCULATION_VERSION,
            'direction': direction,
            'strength': strength,
            'burden_z': round(z, 3),
            'drivers': drivers,
            'evidence': {'daily_state_records': s['states'],
                         'emission_source': s['emission_src']},
            'assumptions': [
                'sell_fraction unmeasured: burden is structural creation load, '
                'not observed miner selling',
                'bid_notional_20 is top-20-level resting notional, not full book',
                'cross-venue sum mixes CoinEx+Gate books; venue-of-truth '
                'weighting arrives with SafeTrade egress',
            ],
            'confidence': 'medium' if s['trades_n'] > 50 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['burden_z'], reverse=True)
    return out


FLOW_VERSION = "flow_pressure_v1"


def build_flow_signals(date):
    """flow_pressure_v1: measured venue trade flow vs resting book.

    absorption = buy_notional / sell_notional (24h, cross-venue).
    sell_load  = sell_notional / bid_notional_20 (can the book take it?).
    Direction from cross-sectional z of net-flow-imbalance; strength
    logistic. Disclosed: venue flow only (CoinEx+Gate), NOT miner-attributed.
    """
    states = read_states(date) + read_states(date, 'safetrade')
    agg = {}
    for s in states:
        sym = (s.get('symbol') or '').upper()
        a = agg.setdefault(sym, {'buy': 0.0, 'sell': 0.0, 'bid': 0.0,
                                 'trades': 0, 'records': []})
        a['buy'] += s.get('trade_buy_notional') or 0
        a['sell'] += s.get('trade_sell_notional') or 0
        a['bid'] += s.get('bid_notional_20_mean') or 0
        a['trades'] += s.get('n_trades') or 0
        if s.get('record_id'):
            a['records'].append(s['record_id'])
    scored = []
    for sym, a in agg.items():
        tot = a['buy'] + a['sell']
        if tot <= 0 or a['trades'] < 5:
            continue
        imb = (a['buy'] - a['sell']) / tot
        sell_load = a['sell'] / a['bid'] if a['bid'] > 0 else None
        scored.append({'symbol': sym, 'imb': imb, 'sell_load': sell_load,
                       'buy': a['buy'], 'sell': a['sell'],
                       'records': a['records'], 'trades': a['trades']})
    if len(scored) < 4:
        print(f"[FLOW {date}] insufficient cross-section ({len(scored)}) — refusing")
        return []
    zs = zscore([s['imb'] for s in scored])
    out = []
    for s, z in zip(scored, zs):
        direction = 'bullish' if z > 0.5 else ('bearish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        sig = {
            'asset': s['symbol'], 'signal': 'flow_pressure',
            'version': FLOW_VERSION, 'calculation_version': CALCULATION_VERSION,
            'direction': direction, 'strength': strength,
            'imbalance_z': round(z, 3),
            'drivers': [f"buy_notional={s['buy']:,.0f}",
                        f"sell_notional={s['sell']:,.0f}",
                        f"sell_load_vs_book={s['sell_load']:.2f}x"
                        if s['sell_load'] else "sell_load_vs_book=n/a"],
            'evidence': {'daily_state_records': s['records']},
            'assumptions': ['venue trade flow only (CoinEx+Gate); not '
                            'miner-attributed until pool graph exists',
                            'thin-history: single-day flow window'],
            'confidence': 'medium' if s['trades'] > 100 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['imbalance_z'])
    return out


REQ_VERSION = "required_flow_v1"


def build_required_signals(date):
    """required_flow_v1: how much buying the day needed to stand still.

    required = emission_usd + sell_notional - buy_notional (floored 0).
    coverage = buy / (emission_usd + sell). Bearish when buying covered
    little of the structural + realized load. Limit-order add/cancel flow
    is unmeasured at daily grain — disclosed, not faked.
    """
    states = read_states(date) + read_states(date, 'safetrade')
    agg = {}
    for s in states:
        sym = (s.get('symbol') or '').upper()
        a = agg.setdefault(sym, {'buy': 0.0, 'sell': 0.0, 'closes': [],
                                 'records': [], 'trades': 0})
        a['buy'] += s.get('trade_buy_notional') or 0
        a['sell'] += s.get('trade_sell_notional') or 0
        if s.get('mid_close'):
            a['closes'].append(s['mid_close'])
        if s.get('record_id'):
            a['records'].append(s['record_id'])
        a['trades'] += s.get('n_trades') or 0
    scored = []
    for sym, a in agg.items():
        emission, esrc = load_emission(sym)
        price = a['closes'][-1] if a['closes'] else None
        if not emission or not price or a['trades'] < 5:
            continue
        em_usd = emission * price
        required = max(0.0, em_usd + a['sell'] - a['buy'])
        denom = em_usd + a['sell']
        coverage = a['buy'] / denom if denom > 0 else None
        scored.append({'symbol': sym, 'required': required,
                       'coverage': coverage, 'em_usd': em_usd,
                       'buy': a['buy'], 'sell': a['sell'],
                       'records': a['records'], 'esrc': esrc,
                       'trades': a['trades']})
    if len(scored) < 4:
        print(f"[REQ {date}] insufficient cross-section ({len(scored)}) — refusing")
        return []
    covs = [s['coverage'] for s in scored if s['coverage'] is not None]
    zs = zscore(covs)
    out = []
    for s, z in zip([x for x in scored if x['coverage'] is not None], zs):
        direction = 'bullish' if z > 0.5 else ('bearish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        sig = {
            'asset': s['symbol'], 'signal': 'required_flow',
            'version': REQ_VERSION, 'calculation_version': CALCULATION_VERSION,
            'direction': direction, 'strength': strength,
            'coverage_z': round(z, 3),
            'drivers': [f"required_buy_usd={s['required']:,.0f}",
                        f"coverage={s['coverage']:.2f}",
                        f"emission_usd={s['em_usd']:,.0f}"],
            'evidence': {'daily_state_records': s['records'],
                         'emission_source': s['esrc']},
            'assumptions': ['miner sells proxied by full emission (upper bound); '
                            'realization unmeasured',
                            'limit add/cancel flow unmeasured at daily grain'],
            'confidence': 'medium' if s['trades'] > 100 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['coverage_z'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    sigs = build_signals(date)
    for s in sigs:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s.get('burden_z', s.get('imbalance_z')):+.2f} | {' '.join(s['drivers'])}")
    print(f"[SIGNALS {date}] {len(sigs)} signals ({SIGNAL_VERSION})")
    flows = build_flow_signals(date)
    for s in flows:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s['imbalance_z']:+.2f} | {' '.join(s['drivers'])}")
    print(f"[FLOW {date}] {len(flows)} signals ({FLOW_VERSION})")
    reqs = build_required_signals(date)
    for s in reqs:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s['coverage_z']:+.2f} | {' '.join(s['drivers'])}")
    print(f"[REQ {date}] {len(reqs)} signals ({REQ_VERSION})")


if __name__ == '__main__':
    main()
