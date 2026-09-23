"""
BTC chain history backfill — free, no key, no node.

Pulls 1 year of daily mining-economics series from the Blockchain.com
Charts API (hash-rate, difficulty, miners-revenue, transaction-fees)
into normalized chain_snapshot rows with point-in-time event_time.
Same auto-archive provenance as live polls (fetch_json archives raw).

This is the BTC-side history the baseline needs: hashrate response,
difficulty lags, security-spend series — the Dune-type dataset,
reconstructable nowhere else once archived with our timestamps.

Usage:
    python3 scripts/load_btc_history.py
"""

import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

CHARTS = {
    # chart-name: (field, unit-note)
    'hash-rate': ('network_hashrate_ths', 'TH/s as reported'),
    'difficulty': ('difficulty', 'absolute difficulty'),
    'miners-revenue': ('miners_revenue_usd', 'USD/day coinbase+fees'),
    'transaction-fees-usd': ('fees_usd_day', 'USD/day fees only'),
}


def main():
    total = 0
    for chart, (field, unit) in CHARTS.items():
        data = fetch_json(
            f'https://api.blockchain.info/charts/{chart}'
            '?timespan=1year&format=json',
            source_id='blockchaininfo-charts', chain_id='btc')
        values = (data or {}).get('values', []) if isinstance(data, dict) else []
        n = 0
        for pt in values:
            try:
                ts, val = pt['x'], float(pt['y'])
            except (KeyError, TypeError, ValueError):
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d')
            store_normalized('chain_snapshot', 'btc', {
                field: val,
                'hashrate_unit': unit if field == 'network_hashrate_ths' else None,
                'source_role': 'history-backfill',
                'source_id': f'blockchaininfo-charts/{chart}',
            }, event_time=dt)
            n += 1
        print(f"  [{chart}] {n} daily points")
        total += n
    print(f"[BTC HISTORY] {total} rows at {utcnow()}")


if __name__ == '__main__':
    main()
