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
    return e, f"chain_fundamentals.json:{symbol}.daily_emission"


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    sigs = build_signals(date)
    for s in sigs:
        print(f"  {s['asset']:6} {s['direction']:8} {s['strength']:.2f} "
              f"z={s['burden_z']:+.2f} | {' '.join(s['drivers'])}")
    print(f"[SIGNALS {date}] {len(sigs)} signals ({SIGNAL_VERSION})")


if __name__ == '__main__':
    main()
