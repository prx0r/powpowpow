"""
Nightly card snapshot — miner-margin history.

Generates live cards for every coin with a STATE price and stores one
row per (coin, hardware) in miner_card. This is what turns "margin
today" into margin history (Seesaw supply-response analysis).

Usage:
    python3 scripts/snapshot_cards.py --date 2026-09-19
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import store_normalized  # noqa: E402
from v1_live_cards import generate_card, asset_of  # noqa: E402


def latest_prices(date=None):
    """Latest mid per canonical ASSET across venues (+ evidence)."""
    best = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'daily_state',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if date and r.get('date') != date:
                    continue
                asset = asset_of(r.get('symbol'))
                if not asset or not r.get('mid_close'):
                    continue
                stamp = r.get('observed_at', '') or r.get('date', '')
                cur = best.get(asset)
                if cur is None or stamp > cur[0]:
                    best[asset] = (stamp, r['mid_close'], r.get('record_id'),
                                   r.get('venue'))
    return {a: {'price': v[1], 'record_id': v[2], 'venue': v[3]}
            for a, v in best.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    prices = latest_prices(date if date != datetime.now(timezone.utc).strftime('%Y-%m-%d') else None)
    n = 0
    for asset, p in sorted(prices.items()):
        price = p['price']
        if not price:
            continue
        try:
            card = generate_card(asset, price)
        except Exception as e:
            print(f"  [{asset}] ERR {str(e)[:100]}")
            continue
        for hw, h in (card.get('hardware') or {}).items():
            store_normalized('miner_card', 'venue', {
                'coin': asset, 'hardware': hw, 'date': date,
                'price_usd': price,
                'price_venue': p.get('venue'),
                'price_evidence': p.get('record_id'),
                'revenue_usd_day': h.get('revenue_usd_day'),
                'electricity_usd_day': h.get('electricity_usd_day'),
                'hw_amort_usd_day': h.get('hw_amort_usd_day'),
                'net_profit_usd_day': h.get('net_profit_usd_day'),
                'payback_days': h.get('payback_days'),
                'calculation_version': card.get('calculation_version'),
            }, event_time=date)
            n += 1
    print(f"[CARDS {date}] {n} hardware rows from {len(prices)} assets")


if __name__ == '__main__':
    main()
