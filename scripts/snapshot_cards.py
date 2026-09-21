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
from v1_live_cards import generate_card  # noqa: E402


def latest_prices(date=None):
    prices = {}
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
                if r.get('mid_close') and r.get('symbol') not in prices:
                    prices[r['symbol']] = r['mid_close']
    return prices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    prices = latest_prices(date if date != datetime.now(timezone.utc).strftime('%Y-%m-%d') else None)
    n = 0
    for coin, price in sorted(prices.items()):
        if not price:
            continue
        try:
            card = generate_card(coin, price)
        except Exception as e:
            print(f"  [{coin}] ERR {str(e)[:100]}")
            continue
        for hw, h in (card.get('hardware') or {}).items():
            store_normalized('miner_card', 'venue', {
                'coin': coin, 'hardware': hw, 'date': date,
                'price_usd': price,
                'revenue_usd_day': h.get('revenue_usd_day'),
                'electricity_usd_day': h.get('electricity_usd_day'),
                'hw_amort_usd_day': h.get('hw_amort_usd_day'),
                'net_profit_usd_day': h.get('net_profit_usd_day'),
                'payback_days': h.get('payback_days'),
                'calculation_version': card.get('calculation_version'),
            }, event_time=date)
            n += 1
    print(f"[CARDS {date}] {n} hardware rows from {len(prices)} coins")


if __name__ == '__main__':
    main()
