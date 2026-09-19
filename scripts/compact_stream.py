"""
Streaming Parquet compactor — constant memory on GB-scale tables.

Walks one date-dir at a time, converts JSONL to Parquet via
ParquetWriter in 50k-row batches, writes a manifest entry, and with
--drop-source removes the date dir afterwards. Recovers GBs from seed
loads: seed JSONL -> ~1/17th the bytes.

Usage:
    python3 scripts/compact_stream.py --date 2026-07-01 [--drop-source]
    python3 scripts/compact_stream.py --all-seeds [--drop-source]
"""

import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pyarrow as pa
import pyarrow.parquet as pq

PARQ_DIR = os.path.join(BASE_DIR, 'warehouse', 'parquet')
MANIFEST = os.path.join(PARQ_DIR, '_manifest.jsonl')
os.makedirs(PARQ_DIR, exist_ok=True)

BATCH = 50000
SEED_DATES = ['2026-07-01', '2026-08-01', '2026-09-01',
              '2026-06-30', '2026-07-31', '2026-08-31']


def encode(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, default=str)


def compact_dir(table, chain, date, drop_source=False):
    src = os.path.join(BASE_DIR, 'warehouse', 'normalized', table,
                       f'chain={chain}', f'date={date}')
    if not os.path.isdir(src):
        return None
    out_dir = os.path.join(PARQ_DIR, table, f'chain={chain}', f'date={date}')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'part.parquet')
    tmp = out + '.tmp'
    writer, schema, rows = None, None, []
    n = 0

    def flush():
        nonlocal writer, schema, rows
        if not rows:
            return
        keys = sorted({k for r in rows for k in r})
        cols = {}
        for k in keys:
            col = [r.get(k) for r in rows]
            if len({type(v).__name__ for v in col if v is not None}) > 1:
                col = [None if v is None else str(v) for v in col]
            cols[k] = col
        batch = pa.table(cols)
        if writer is None:
            schema = batch.schema
            writer = pq.ParquetWriter(tmp, schema, compression='zstd',
                                      compression_level=9,
                                      write_statistics=True)
        else:
            batch = batch.cast(schema)
        writer.write_table(batch)
        n_iter[0] += len(rows)
        rows = []
        return rows

    n_iter = [0]
    src_bytes = 0
    for f in sorted(glob.glob(os.path.join(src, 'hour=*.jsonl'))):
        src_bytes += os.path.getsize(f)
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                rows.append({k: encode(v) for k, v in r.items()})
                if len(rows) >= BATCH:
                    rows = flush() or []
    rows = flush() or rows
    if writer is None:
        return None
    writer.close()
    os.replace(tmp, out)
    entry = {'at': datetime.now(timezone.utc).isoformat(), 'table': table,
             'chain': chain, 'date': date, 'rows': n_iter[0],
             'src_bytes': src_bytes, 'parquet_bytes': os.path.getsize(out),
             'ratio': round(src_bytes / max(os.path.getsize(out), 1), 2)}
    with open(MANIFEST, 'a') as fh:
        fh.write(json.dumps(entry) + '\n')
    if drop_source:
        shutil.rmtree(src)
        entry['dropped_source'] = True
    print(f"  {table}/{chain}/{date}: {n_iter[0]:,} rows "
          f"{src_bytes/1e6:.0f}MB -> {entry['parquet_bytes']/1e6:.1f}MB "
          f"({entry['ratio']}x){' DROPPED' if drop_source else ''}",
          flush=True)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    ap.add_argument('--all-seeds', action='store_true')
    ap.add_argument('--drop-source', action='store_true')
    ap.add_argument('--table', default=None)
    args = ap.parse_args()
    dates = SEED_DATES if args.all_seeds else [args.date or '2026-09-19']
    norm = os.path.join(BASE_DIR, 'warehouse', 'normalized')
    tables = [args.table] if args.table else sorted(os.listdir(norm))
    for date in dates:
        for table in tables:
            if not os.path.isdir(os.path.join(norm, table)):
                continue
            for chain in ('venue', 'safetrade'):
                try:
                    compact_dir(table, chain, date, args.drop_source)
                except Exception as e:
                    print(f"  ERR {table}/{chain}/{date}: {str(e)[:150]}")


if __name__ == '__main__':
    main()
