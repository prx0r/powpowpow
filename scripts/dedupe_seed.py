"""
One-time dedupe for seed-date partitions.

The 2026-09-01 KAS book file was killed mid-load after partial bulk
flushes; the rerun rewrites it fully, so some rows exist twice. This
rewrites affected day-partitions keeping the first occurrence per
(trade) venue|symbol|exchange_time|trade_id or (snapshot)
venue|symbol|exchange_time|mid|spread.

Usage:
    python3 scripts/dedupe_seed.py --dates 2026-09-01,2026-08-01,2026-07-01
"""

import argparse
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import row_date


def key_of(r, table):
    base = (r.get('venue'), r.get('symbol'), r.get('exchange_time'))
    if table == 'trade':
        return base + (r.get('trade_id'),)
    return base + (r.get('mid'), r.get('spread_bps'))


def dedupe(dates):
    for table in ('trade', 'orderbook_snapshot'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', table,
                'chain=venue', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                lines = fh.readlines()
            seen, out, drop = set(), [], 0
            for line in lines:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = row_date(r)
                if d in dates and r.get('snapshot_kind') == 'tardis_seed':
                    k = key_of(r, table)
                    if k in seen:
                        drop += 1
                        continue
                    seen.add(k)
                out.append(line)
            if drop:
                with open(f, 'w') as fh:
                    fh.writelines(out)
                print(f"  {os.path.basename(os.path.dirname(os.path.dirname(f)))}/{os.path.basename(f)}: -{drop} dupes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', default='2026-09-01,2026-08-01,2026-07-01')
    args = ap.parse_args()
    dedupe(set(args.dates.split(',')))
    print("[DEDUPE] done")


if __name__ == '__main__':
    main()
