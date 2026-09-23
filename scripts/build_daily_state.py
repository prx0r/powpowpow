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

try:
    from core import row_date, store_normalized  # noqa: E402
except (ImportError, AttributeError):
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location('_core_py',
            os.path.join(BASE_DIR, 'core.py'))
    _core = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_core)
    row_date = _core.row_date
    store_normalized = _core.store_normalized

CALCULATION_VERSION = "daily-state-v1"


def iter_table(table, chain, date):
    """Stream rows for one date. Prefilters on the raw line (exchange/
    receive timestamps are ISO strings containing the date) so GB-scale
    tables never fully load into RAM."""
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', table,
            f'chain={chain}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                if date not in line[:400]:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if row_date(r) == date:
                    yield r


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


def new_acc():
    return {'n_sn': 0, 'open_t': None, 'open_m': None, 'close_t': None,
            'close_m': None, 'hi': None, 'lo': None, 'spreads': [],
            'bid_sum': 0.0, 'bid_n': 0, 'ask_sum': 0.0, 'ask_n': 0,
            'n_tk': 0, 'last_tick': {}, 'last_tick_t': '',
            'n_tr': 0, 'vol': 0.0, 'buy': 0.0, 'sell': 0.0,
            'cov_first': None, 'cov_last': None, 'polls': set()}


def build_day(chain, date):
    acc = {}
    gaps = {}
    for r in iter_table('orderbook_snapshot', chain, date):
        key = (r.get('venue'), r.get('symbol'))
        if not key[0] or not key[1]:
            continue
        a = acc.setdefault(key, new_acc())
        t = r.get('exchange_time') or r.get('receive_time') or ''
        m = fnum(r.get('mid'))
        a['n_sn'] += 1
        if m is not None:
            if a['open_t'] is None or t < a['open_t']:
                a['open_t'], a['open_m'] = t, m
            if a['close_t'] is None or t >= a['close_t']:
                a['close_t'], a['close_m'] = t, m
            a['hi'] = m if a['hi'] is None or m > a['hi'] else a['hi']
            a['lo'] = m if a['lo'] is None or m < a['lo'] else a['lo']
        sp = fnum(r.get('spread_bps'))
        if sp is not None:
            a['spreads'].append(sp)
        b = fnum(r.get('bid_notional_20'))
        if b is None and isinstance(r.get('bids'), list):
            try:
                b = sum(float(p) * float(q) for p, q in r['bids'][:20])
            except (ValueError, TypeError, IndexError):
                b = None
        if b is not None:
            a['bid_sum'] += b
            a['bid_n'] += 1
        k = fnum(r.get('ask_notional_20'))
        if k is None and isinstance(r.get('asks'), list):
            try:
                k = sum(float(p) * float(q) for p, q in r['asks'][:20])
            except (ValueError, TypeError, IndexError):
                k = None
        if k is not None:
            a['ask_sum'] += k
            a['ask_n'] += 1
        rt = r.get('receive_time') or ''
        if a['cov_first'] is None or rt < a['cov_first']:
            a['cov_first'] = rt
        if a['cov_last'] is None or rt > a['cov_last']:
            a['cov_last'] = rt
        if r.get('poll_id') is not None:
            a['polls'].add(r['poll_id'])
    for r in iter_table('ticker', chain, date):
        if isinstance(r.get('tickers'), list):
            continue  # safetrade ws tick bundle
        key = (r.get('venue'), r.get('symbol'))
        if not key[0] or not key[1]:
            continue
        a = acc.setdefault(key, new_acc())
        a['n_tk'] += 1
        t = r.get('receive_time') or ''
        if t >= a['last_tick_t']:
            a['last_tick_t'] = t
            a['last_tick'] = r
    for r in iter_table('trade', chain, date):
        key = (r.get('venue'), r.get('symbol'))
        if not key[0] or not key[1]:
            continue
        a = acc.setdefault(key, new_acc())
        a['n_tr'] += 1
        q, p = fnum(r.get('quantity')), fnum(r.get('price'))
        if q is not None and p is not None:
            n = q * p
            a['vol'] += n
            side = (r.get('aggressor_side') or '').lower()
            if side == 'buy':
                a['buy'] += n
            elif side == 'sell':
                a['sell'] += n
    for r in iter_table('gap_event', chain, date):
        key = (r.get('venue'), r.get('symbol'))
        gaps[key] = gaps.get(key, 0) + 1

    states = []
    for (venue, symbol), a in sorted(acc.items()):
        state = {
            'venue': venue, 'symbol': symbol, 'date': date,
            'calculation_version': CALCULATION_VERSION,
            'n_snapshots': a['n_sn'],
            'n_tickers': a['n_tk'],
            'n_trades': a['n_tr'],
            'mid_open': a['open_m'],
            'mid_high': a['hi'],
            'mid_low': a['lo'],
            'mid_close': a['close_m'],
            'spread_bps_median': median(a['spreads']),
            'bid_notional_20_mean': (a['bid_sum'] / a['bid_n']) if a['bid_n'] else None,
            'ask_notional_20_mean': (a['ask_sum'] / a['ask_n']) if a['ask_n'] else None,
            'trade_notional_sum': a['vol'],
            'trade_buy_notional': a['buy'],
            'trade_sell_notional': a['sell'],
            'last_price': fnum(a['last_tick'].get('last')),
            'day_volume': fnum(a['last_tick'].get('volume')),
            'coverage_first': a['cov_first'],
            'coverage_last': a['cov_last'],
            'poll_ids': sorted(a['polls']),
            'gap_events': gaps.get((venue, symbol), 0),
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
