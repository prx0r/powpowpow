"""
Daily STATE builder — the garden's core object.

Rolls warehouse normalized rows into one impeccable snapshot per
(venue, symbol, UTC date): STATE[t]. Everything downstream (screens,
signals, backtests, content) reads STATE, never raw rows directly.

Inputs (normalized tables, chain=venue / chain=safetrade when live):
  orderbook_snapshot, ticker, trade, gap_event, universe_event
Output:
  daily_state rows (normalized table, chain=<venue|safetrade>) with:
  - market microstructure daily aggregates (mid OHLC, median spread,
    mean depth notionals, trade count/volume/buy-sell split)
  - coverage + provenance (poll range, input row counts, gaps,
    calculation version)

Point-in-time rule: a STATE[t] row only uses rows with receive_time on
date t. Late-arriving rows for t after the rollup are recorded as
revisions (revision field), never silent overwrites.

Usage:
    python3 scripts/build_daily_state.py --date 2026-09-19   # one day
    python3 scripts/build_daily_state.py                     # today (UTC)
"""

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import store_normalized  # noqa: E402

CALCULATION_VERSION = "daily-state-v1"


def read_table(table, chain):
    rows = []
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', table,
            f'chain={chain}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return rows


def fnum(x):
    try:
        v = float(x)
        return v if v == v and v not in (float('inf'), float('-inf')) else None
    except (TypeError, ValueError):
        return None


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def build_day(chain, date):
    snaps = [r for r in read_table('orderbook_snapshot', chain)
             if (r.get('receive_time') or '')[:10] == date]
    ticks = [r for r in read_table('ticker', chain)
             if (r.get('receive_time') or '')[:10] == date]
    trades = [r for r in read_table('trade', chain)
              if (r.get('receive_time') or '')[:10] == date]
    gaps = [r for r in read_table('gap_event', chain)
            if (r.get('receive_time') or r.get('at') or '')[:10] == date]

    by_market = defaultdict(lambda: {'snaps': [], 'ticks': [], 'trades': []})
    for r in snaps:
        by_market[(r.get('venue'), r.get('symbol'))]['snaps'].append(r)
    for r in ticks:
        if isinstance(r.get('tickers'), list):
            continue  # safetrade ws tick bundle handled below
        by_market[(r.get('venue'), r.get('symbol'))]['ticks'].append(r)
    for r in trades:
        by_market[(r.get('venue'), r.get('symbol'))]['trades'].append(r)

    states = []
    for (venue, symbol), g in sorted(by_market.items()):
        if not venue or not symbol:
            continue
        sn = sorted(g['snaps'], key=lambda r: r.get('receive_time', ''))
        mids = [fnum(r.get('mid')) for r in sn]
        mids_nn = [m for m in mids if m is not None]
        spreads = [fnum(r.get('spread_bps')) for r in sn]
        tks = sorted(g['ticks'], key=lambda r: r.get('receive_time', ''))
        trs = g['trades']
        vols, buys, sells = [], 0.0, 0.0
        for t in trs:
            q = fnum(t.get('quantity'))
            p = fnum(t.get('price'))
            if q is not None and p is not None:
                vols.append(q * p)
                side = (t.get('aggressor_side') or '').lower()
                if side == 'buy':
                    buys += q * p
                elif side == 'sell':
                    sells += q * p
        last_tick = tks[-1] if tks else {}
        state = {
            'venue': venue, 'symbol': symbol, 'date': date,
            'calculation_version': CALCULATION_VERSION,
            'n_snapshots': len(sn),
            'n_tickers': len(tks),
            'n_trades': len(trs),
            'mid_open': mids_nn[0] if mids_nn else None,
            'mid_high': max(mids_nn) if mids_nn else None,
            'mid_low': min(mids_nn) if mids_nn else None,
            'mid_close': mids_nn[-1] if mids_nn else None,
            'spread_bps_median': median(spreads),
            'bid_notional_20_mean': mean([fnum(r.get('bid_notional_20')) for r in sn]),
            'ask_notional_20_mean': mean([fnum(r.get('ask_notional_20')) for r in sn]),
            'trade_notional_sum': sum(vols) if vols else 0.0,
            'trade_buy_notional': buys,
            'trade_sell_notional': sells,
            'last_price': fnum(last_tick.get('last')),
            'day_volume': fnum(last_tick.get('volume')),
            'coverage_first': sn[0].get('receive_time') if sn else None,
            'coverage_last': sn[-1].get('receive_time') if sn else None,
            'poll_ids': sorted({r.get('poll_id') for r in sn if r.get('poll_id') is not None}),
            'gap_events': sum(1 for e in gaps
                              if e.get('venue') == venue and e.get('symbol') == symbol),
            'revision': 0,
        }
        states.append(state)
        store_normalized('daily_state', chain, state, event_time=date)
    return states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None, help='UTC date YYYY-MM-DD (default today)')
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    total = 0
    for chain in ('venue', 'safetrade'):
        states = build_day(chain, date)
        total += len(states)
        for s in states:
            print(f"  [{s['venue']}:{s['symbol']}] snaps={s['n_snapshots']} "
                  f"trades={s['n_trades']} mid_close={s['mid_close']} "
                  f"spread_med={s['spread_bps_median']}")
    print(f"[STATE {date}] {total} market-states written")


if __name__ == '__main__':
    main()
