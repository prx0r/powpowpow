"""
Hot-window trim — keep 7 days of JSONL, Parquet holds the rest.

For heavy tables (trade, orderbook_snapshot, ticker): remove date dirs
older than --days UNLESS no Parquet part exists for that date (never
drop uncompacted data). Derived tables (daily_state, signals, gaps,
chain telemetry) are tiny — kept forever.

Usage:
    python3 scripts/trim_jsonl.py --days 7
"""

import argparse
import glob
import os
import shutil
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

HEAVY = ('trade', 'orderbook_snapshot', 'ticker')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    args = ap.parse_args()
    today = datetime.now(timezone.utc).date().isoformat()
    freed, kept_uncompacted = 0, []
    norm = os.path.join(BASE_DIR, 'warehouse', 'normalized')
    parq = os.path.join(BASE_DIR, 'warehouse', 'parquet')
    for table in HEAVY:
        for chain_dir in glob.glob(os.path.join(norm, table, 'chain=*')):
            for date_dir in glob.glob(os.path.join(chain_dir, 'date=*')):
                date = os.path.basename(date_dir)[5:]
                if date >= today:
                    continue
                age = (datetime.fromisoformat(today).date() -
                       datetime.fromisoformat(date).date()).days
                if age <= args.days:
                    continue
                chain = os.path.basename(chain_dir)[6:]
                pq_part = os.path.join(parq, table, f'chain={chain}', f'date={date}',
                                       'part.parquet')
                if not os.path.exists(pq_part):
                    kept_uncompacted.append(f'{table}/{chain}/{date}')
                    continue
                size = sum(os.path.getsize(os.path.join(r, f))
                           for r, _, fs in os.walk(date_dir) for f in fs)
                shutil.rmtree(date_dir)
                freed += size
    print(f"[TRIM] freed {freed/1e6:.1f}MB, kept-uncompacted: {kept_uncompacted or 'none'}")


if __name__ == '__main__':
    main()
