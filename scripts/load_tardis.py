"""
Tardis seed loader — free first-of-month CSVs into normalized tables.

Reads warehouse/tardis/*.csv.gz (trades, book_snapshot_25) and writes
normalized trade + orderbook_snapshot rows with venue mapped to our
namespace (gate-io->gate, mexc->mexc), symbols de-suffixed (KAS_USDT->KAS),
exchange_time preserved (microsecond exchange timestamps), and
source/snapshot_kind marked tardis_seed. Point-in-time safe: readers key
on exchange_time via core.row_date.

Idempotent-ish: skips files listed in warehouse/tardis/_loaded.json.

Usage:
    python3 scripts/load_tardis.py
"""

import csv
import gzip
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402 (bulk writer below matches store_normalized format)

TARDIS_DIR = os.path.join(BASE_DIR, 'warehouse', 'tardis')
LOADED_FILE = os.path.join(TARDIS_DIR, '_loaded.json')

VENUE_MAP = {'gate-io': 'gate', 'mexc': 'mexc'}

# Bulk buffer: (table, chain, date, hour) -> rows. Per-row
# store_normalized does open/append/close (~ms each); seeds are millions
# of rows, so we write each hour-file once. Format matches core exactly.
BULK = {}
BULK_FLUSH_ROWS = 200000


def bulk_put(table, chain_id, data, event_time=None):
    observed_at = utcnow()
    hour_key = (event_time or observed_at)[:13]  # YYYY-MM-DDTHH
    date, hour = hour_key[:10], hour_key[11:13]
    key = (table, chain_id, date, hour)
    BULK.setdefault(key, []).append({
        'record_id': f"{chain_id}_{table}_{observed_at}",
        'raw_event_id': None, 'network_id': chain_id,
        'event_time': event_time, 'observed_at': observed_at,
        'normalized_at': observed_at, 'schema_name': table,
        'schema_version': '1.0', 'normalizer_version': '1.0.0', **data})
    if sum(len(v) for v in BULK.values()) >= BULK_FLUSH_ROWS:
        flush_bulk()


def flush_bulk():
    from collections import defaultdict
    for (table, chain_id, date, hour), rows in list(BULK.items()):
        d = os.path.join(BASE_DIR, 'warehouse', 'normalized', table,
                         f'chain={chain_id}', f'date={date}')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'hour={hour}.jsonl'), 'a') as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + '\n')
        del BULK[(table, chain_id, date, hour)]


def sym_of(venue, symbol):
    s = symbol.upper()
    for suf in ('_USDT', 'USDT', '_USDC', 'USDC'):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s


def us_to_iso(us):
    try:
        return datetime.fromtimestamp(int(us) / 1e6, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def load_loaded():
    try:
        return set(json.load(open(LOADED_FILE)))
    except (OSError, ValueError):
        return set()


def save_loaded(done):
    with open(LOADED_FILE, 'w') as f:
        json.dump(sorted(done), f, indent=2)


def load_trades(path, venue, symbol):
    n = 0
    with gzip.open(path, 'rt') as fh:
        for row in csv.DictReader(fh):
            et = us_to_iso(row.get('timestamp'))
            bulk_put('trade', 'venue', {
                'venue': venue, 'symbol': symbol,
                'market': row.get('symbol'),
                'receive_time': us_to_iso(row.get('local_timestamp')) or et,
                'exchange_time': et,
                'trade_id': row.get('id'), 'price': row.get('price'),
                'quantity': row.get('amount'),
                'aggressor_side': (row.get('side') or '').lower(),
                'snapshot_kind': 'tardis_seed',
                'source_role': 'tardis_seed',
                'tardis_file': os.path.basename(path),
            }, event_time=et)
            n += 1
    return n


def load_books(path, venue, symbol):
    n = 0
    with gzip.open(path, 'rt') as fh:
        for row in csv.DictReader(fh):
            bids, asks = [], []
            for i in range(25):
                bp, ba = row.get(f'bids[{i}].price'), row.get(f'bids[{i}].amount')
                ap, aa = row.get(f'asks[{i}].price'), row.get(f'asks[{i}].amount')
                if bp and ba:
                    bids.append([bp, ba])
                if ap and aa:
                    asks.append([ap, aa])
            if not bids or not asks:
                continue
            try:
                mid = (float(bids[0][0]) + float(asks[0][0])) / 2
                spread = (float(asks[0][0]) - float(bids[0][0])) / mid * 10000
            except (ValueError, ZeroDivisionError):
                mid, spread = None, None
            bands = {}
            if mid:
                for bps in (10, 25, 50, 100, 500):
                    lim = bps / 10000
                    try:
                        bn = sum(float(p) * float(q) for p, q in bids
                                 if float(p) >= mid * (1 - lim))
                        an = sum(float(p) * float(q) for p, q in asks
                                 if float(p) <= mid * (1 + lim))
                        bands[f'bid_{bps}bps'] = round(bn, 2)
                        bands[f'ask_{bps}bps'] = round(an, 2)
                    except ValueError:
                        pass
            et = us_to_iso(row.get('timestamp'))
            try:
                b20 = sum(float(p) * float(q) for p, q in bids[:20])
                a20 = sum(float(p) * float(q) for p, q in asks[:20])
            except ValueError:
                b20, a20 = None, None
            bulk_put('orderbook_snapshot', 'venue', {
                'venue': venue, 'symbol': symbol, 'market': row.get('symbol'),
                'receive_time': us_to_iso(row.get('local_timestamp')) or et,
                'exchange_time': et, 'mid': mid, 'spread_bps': spread,
                **bands, 'bid_notional_20': b20, 'ask_notional_20': a20,
                'bid_levels': len(bids), 'ask_levels': len(asks),
                'bids': bids, 'asks': asks,
                'snapshot_kind': 'tardis_seed',
                'source_role': 'tardis_seed',
                'tardis_file': os.path.basename(path),
            }, event_time=et)
            n += 1
    flush_bulk()
    return n


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--include', default='', help='substring filter on filenames')
    ap.add_argument('--exclude', default='', help='substring filter to skip')
    args = ap.parse_args()
    done = load_loaded()
    files = sorted(f for f in os.listdir(TARDIS_DIR) if f.endswith('.csv.gz'))
    if args.include:
        files = [f for f in files if args.include in f]
    if args.exclude:
        files = [f for f in files if args.exclude not in f]
    t_total = b_total = 0
    for fn in files:
        if fn in done:
            continue
        # gate-io_KAS_USDT_book_snapshot_25_20260901.csv.gz
        # mexc_NOCKUSDT_trades_20260901.csv.gz
        body = fn[:-7]
        if '_book_snapshot_25_' in body:
            dtype = 'book_snapshot_25'
            rest = body.split('_book_snapshot_25_')[0]
        elif '_trades_' in body:
            dtype = 'trades'
            rest = body.split('_trades_')[0]
        else:
            print(f"  SKIP {fn} (unknown dtype)")
            continue
        ex, _, sym_raw = rest.partition('_')
        if not sym_raw:  # mexc_NOCKUSDT... has no '_' after exchange
            sym_raw = rest[len(ex):]
        venue = VENUE_MAP.get(ex, ex)
        symbol = sym_of(venue, sym_raw)
        path = os.path.join(TARDIS_DIR, fn)
        try:
            if dtype == 'trades':
                n = load_trades(path, venue, symbol)
                t_total += n
            elif dtype == 'book_snapshot_25':
                n = load_books(path, venue, symbol)
                b_total += n
            else:
                print(f"  SKIP {fn} (unknown dtype)")
                continue
            done.add(fn)
            save_loaded(done)
            print(f"  {fn}: {n:,} rows -> {venue}:{symbol}")
        except Exception as e:
            print(f"  ERR {fn}: {str(e)[:150]}")
    flush_bulk()
    print(f"[TARDIS] +{t_total:,} trades, +{b_total:,} snapshots")


if __name__ == '__main__':
    main()
