"""
XMR chain history backfill — explorer.xmr.club (free, no key).

~120 points (~3-day grain) of network hashrate + difficulty with
heights, from the mempool.space-fork index (indexed from May 2026).
The only free XMR chain history found (verified 2026-09-23):
moneroblocks.info and hashrate.no expose live-only data;
oanor needs a key; CoinWarz history is HTML-only.

Grain note: ~3-day averages, NOT daily. Downstream joins must
tolerate grain (forward-fill, never pretend daily resolution).

Usage:
    python3 scripts/load_xmr_history.py
"""

import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402


def main():
    data = fetch_json('https://explorer.xmr.club/api/v1/mining/hashrate/1y',
                      source_id='xmrclub-mining', chain_id='xmr')
    if not isinstance(data, dict):
        print("[XMR HISTORY] fetch failed")
        return
    by_ts = {}
    for pt in data.get('hashrates', []) or []:
        try:
            by_ts[pt['timestamp']] = {'hr': float(pt['avgHashrate']),
                                      'height': pt.get('avgHeight')}
        except (KeyError, TypeError, ValueError):
            continue
    for pt in data.get('difficulty', []) or []:
        try:
            e = by_ts.setdefault(pt['timestamp'], {})
            e['diff'] = float(pt['difficulty'])
            e.setdefault('height', pt.get('height'))
        except (KeyError, TypeError, ValueError):
            continue
    n = 0
    for ts in sorted(by_ts):
        e = by_ts[ts]
        if 'hr' not in e and 'diff' not in e:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
        store_normalized('chain_snapshot', 'xmr', {
            'height': e.get('height'),
            'difficulty': e.get('diff'),
            'network_hashrate': e.get('hr'),
            'hashrate_unit': 'H/s (xmr.club avgHashrate)',
            'grain': '~3-day average (120 pts/yr)',
            'source_role': 'history-backfill',
            'source_id': 'xmrclub-mining/hashrate-1y',
        }, event_time=dt)
        n += 1
    print(f"[XMR HISTORY] {n} points "
          f"(current hashrate {(data.get('currentHashrate') or 0)/1e9:.2f} GH/s) "
          f"at {utcnow()}")


if __name__ == '__main__':
    main()
