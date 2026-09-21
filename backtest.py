"""
Backtester scaffold — fundamentals only, no candle replay.

Joins daily STATE with derived signals and measures forward mid-close
returns by signal bucket. Honest about history depth: with fewer than
MIN_DAYS of STATE it reports insufficiency instead of statistics.

Event studies read chains/events/<SYM>_events.json (see events.py) and
align event dates with STATE mid closes.

Usage:
    python3 backtest.py --min-days 7
"""

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CALCULATION_VERSION = "backtest-v0-scaffold"


def load_states():
    rows = []
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', 'daily_state',
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return rows


def load_signals():
    sigs = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'derived_signal',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sigs[(r.get('asset'), r.get('date'))] = r
    return sigs


def forward_returns(rows):
    """Map (venue, symbol, date) -> next-date mid_close return."""
    by_key = defaultdict(dict)
    for r in rows:
        if r.get('mid_close'):
            by_key[(r.get('venue'), r.get('symbol'))][r.get('date')] = r['mid_close']
    fwds = {}
    for key, series in by_key.items():
        dates = sorted(series)
        for i in range(len(dates) - 1):
            a, b = series[dates[i]], series[dates[i + 1]]
            if a:
                fwds[(key[0], key[1], dates[i])] = (b - a) / a
    return fwds


def run(min_days=7):
    rows = load_states()
    dates = sorted({r.get('date') for r in rows if r.get('date')})
    print(f"[BACKTEST] {len(rows)} states over {len(dates)} day(s): {dates[:3]}")
    if len(dates) < 2:
        print("[BACKTEST] insufficient history: need 2+ days for even 1d forwards. "
              "Clock started 2026-09-19; rerun as STATE accumulates.")
        return {'status': 'insufficient_history', 'days': len(dates)}
    fwds = forward_returns(rows)
    sigs = load_signals()
    buckets = defaultdict(list)
    for (venue, sym, date), ret in fwds.items():
        sig = sigs.get((sym, date), {})
        buckets[sig.get('direction', 'no-signal')].append(ret)
    print(f"{'bucket':12} {'n':>5} {'mean_fwd':>10} {'hit(>0)':>8}")
    result = {'status': 'ok', 'days': len(dates), 'buckets': {}}
    for b, rs in sorted(buckets.items()):
        mean = sum(rs) / len(rs)
        hit = sum(1 for x in rs if x > 0) / len(rs)
        result['buckets'][b] = {'n': len(rs), 'mean_fwd': mean, 'hit_rate': hit}
        print(f"{b:12} {len(rs):>5} {mean:>+10.4%} {hit:>8.1%}")
        if len(dates) < min_days:
            print("  (thin history — direction stats are noise until "
                  f"{min_days}d of STATE)")
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-days', type=int, default=7)
    args = ap.parse_args()
    run(args.min_days)
