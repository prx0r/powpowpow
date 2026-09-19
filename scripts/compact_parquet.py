"""
Parquet compactor — keep every tick, pay ~nothing.

Rolls warehouse/normalized JSONL tables into partitioned Parquet
(warehouse/parquet/<table>/date=YYYY-MM-DD/part.parquet, zstd), with a
manifest recording rows/bytes/ratio per partition. Full L2 levels ride
along as JSON-encoded columns (zstd still crushes them); bands, mids,
and spreads stay native for pushdown.

Raw JSON stays the immutable audit trail. Query layer becomes
Parquet-via-DuckDB; JSONL sources kept until --drop-source is passed
after a verified compact.

Usage:
    python3 scripts/compact_parquet.py --date 2026-09-19
    python3 scripts/compact_parquet.py --date 2026-09-19 --drop-source
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pyarrow as pa
import pyarrow.parquet as pq

PARQ_DIR = os.path.join(BASE_DIR, 'warehouse', 'parquet')
MANIFEST = os.path.join(PARQ_DIR, '_manifest.jsonl')
os.makedirs(PARQ_DIR, exist_ok=True)


def encode(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, default=str)


def compact_table(table, date, drop_source=False):
    files = sorted(glob.glob(os.path.join(
        BASE_DIR, 'warehouse', 'normalized', table,
        'chain=*', 'date=*', 'hour=*.jsonl')))
    rows, src_bytes = [], 0
    used = []
    for f in files:
        hit = False
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            stamp = r.get('receive_time') or r.get('generated_at') \
                or r.get('date') or r.get('timestamp') or ''
            if stamp[:10] != date:
                continue
            hit = True
            rows.append({k: encode(v) for k, v in r.items()})
        if hit:
            src_bytes += os.path.getsize(f)
            used.append(f)
    if not rows:
        return None
    keys = sorted({k for r in rows for k in r})
    cols = {k: [r.get(k) for r in rows] for k in keys}
    # Coerce mixed-type columns to string (parquet is strict).
    for k, col in cols.items():
        types = {type(v).__name__ for v in col if v is not None}
        if len(types) > 1:
            cols[k] = [None if v is None else str(v) for v in col]
    out_dir = os.path.join(PARQ_DIR, table, f'date={date}')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'part.parquet')
    pq.write_table(pa.table(cols), out, compression='zstd',
                   compression_level=9, write_statistics=True)
    pq_bytes = os.path.getsize(out)
    entry = {'at': datetime.now(timezone.utc).isoformat(), 'table': table,
             'date': date, 'rows': len(rows), 'src_bytes': src_bytes,
             'parquet_bytes': pq_bytes,
             'ratio': round(src_bytes / max(pq_bytes, 1), 2),
             'sources': len(used)}
    with open(MANIFEST, 'a') as fh:
        fh.write(json.dumps(entry) + '\n')
    if drop_source:
        for f in used:
            os.remove(f)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    ap.add_argument('--table', default=None)
    ap.add_argument('--drop-source', action='store_true')
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    tables = [args.table] if args.table else sorted(os.listdir(
        os.path.join(BASE_DIR, 'warehouse', 'normalized')))
    total_src = total_pq = total_rows = 0
    for t in tables:
        if not os.path.isdir(os.path.join(BASE_DIR, 'warehouse', 'normalized', t)):
            continue
        e = compact_table(t, date, args.drop_source)
        if e:
            total_src += e['src_bytes']
            total_pq += e['parquet_bytes']
            total_rows += e['rows']
            print(f"  {t:20} rows={e['rows']:>7,} "
                  f"{e['src_bytes']/1e6:>8.1f}MB -> {e['parquet_bytes']/1e6:>6.1f}MB "
                  f"({e['ratio']}x)")
    if total_rows:
        print(f"[COMPACT {date}] {total_rows:,} rows, "
              f"{total_src/1e6:.1f}MB -> {total_pq/1e6:.1f}MB "
              f"({total_src/max(total_pq,1):.1f}x)")
    else:
        print(f"[COMPACT {date}] no rows")


if __name__ == '__main__':
    main()
