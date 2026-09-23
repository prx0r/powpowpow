"""
BTC trade-flow backfill — Binance Vision public archive (free, no key).

Books are unrecoverable anywhere free (same as XMR/QUBIC — live books
are the moat). But BTC TRADES are backfillable: daily aggTrades zips
(~3-15MB) carry price/qty/timestamp/aggressor side. Derive hourly
flow bars (buy/sell notionals + counts, VWAP, OHLC) into normalized
`flow_bars` — the historical buy/sell-imbalance series that live
flow_pressure only measures from today.

Raw zips are NOT hoarded: they are re-fetchable public URLs
(backfillable truth per backfill.md doctrine). Download to tmp,
stream-parse, delete. Provenance recorded per bar (source URL).

aggTrades CSV: aggTradeId,price,quantity,firstTradeId,lastTradeId,
timestamp,isBuyerMaker,isBestMatch. isBuyerMaker=true → seller-
initiated (sell); false → buyer-initiated (buy).

Usage:
    python3 scripts/backfill_btc_trades.py --months 3
    python3 scripts/backfill_btc_trades.py --months 12 --start 2025-10
"""

import argparse
import csv
import hashlib
import os
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import store_normalized, utcnow  # noqa: E402

BASE_URL = 'https://data.binance.vision/data/spot'
# NOTE: monthly zips stall ~357MB through this VPS's CloudFront path
# (verified 2x, byte-identical stall point). Daily zips (~3-15MB) work.
# Always use daily granularity regardless of --months.


def month_range(start, n):
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return out


def days_in_month(ym):
    import calendar
    y, m = int(ym[:4]), int(ym[5:7])
    return [f"{ym}-{d:02d}" for d in range(1, calendar.monthrange(y, m)[1] + 1)]


def fetch_daily(day, tmpdir, retries=3):
    import requests
    name = f'BTCUSDT-aggTrades-{day}.zip'
    url = f'{BASE_URL}/daily/aggTrades/BTCUSDT/{name}'
    zp = os.path.join(tmpdir, name)
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url + '.CHECKSUM', timeout=30,
                             headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                return None  # day not published (future/current day)
            expected = r.text.split()[0]
            with requests.get(url, timeout=(15, 60), stream=True,
                              headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                resp.raise_for_status()
                h = hashlib.sha256()
                with open(zp, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        if chunk:
                            h.update(chunk)
                            f.write(chunk)
            if h.hexdigest() != expected:
                print(f"  [{day}] CHECKSUM MISMATCH (try {attempt}), retrying")
                continue
            return zp
        except Exception as e:
            print(f"  [{day}] fetch try {attempt} failed: {str(e)[:100]}")
            time.sleep(5 * attempt)
    return None


def fetch_month(ym, tmpdir, retries=3):
    raise RuntimeError("monthly zips stall on this egress; use fetch_daily")


def parse_bars(zp):
    """Stream zip -> hourly bars. Returns {hour_str: agg dict}."""
    bars = defaultdict(lambda: {'buy_n': 0.0, 'sell_n': 0.0, 'buy_c': 0,
                                'sell_c': 0, 'o': None, 'h': None,
                                'l': None, 'c': None})
    n = 0
    with zipfile.ZipFile(zp) as z:
        inner = [i for i in z.namelist() if i.endswith('.csv')][0]
        with z.open(inner) as f:
            import io
            rdr = csv.reader(io.TextIOWrapper(f))
            for row in rdr:
                try:
                    if not row[0].lstrip('-').isdigit():
                        continue  # header row
                    price, qty = float(row[1]), float(row[2])
                    ts = int(row[5])
                    # Magnitude-normalize: ms (1e12) or us (1e15) -> seconds.
                    while ts > 1e11:
                        ts //= 1000
                    buy_maker = row[6].lower() == 'true'
                except (IndexError, ValueError):
                    continue
                hour = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%dT%H')
                b = bars[hour]
                notional = price * qty
                if buy_maker:
                    b['sell_n'] += notional
                    b['sell_c'] += 1
                else:
                    b['buy_n'] += notional
                    b['buy_c'] += 1
                b['c'] = price
                if b['o'] is None:
                    b['o'] = price
                b['h'] = price if b['h'] is None else max(b['h'], price)
                b['l'] = price if b['l'] is None else min(b['l'], price)
                n += 1
    return bars, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', type=int, default=3)
    ap.add_argument('--start', default=None,
                    help='YYYY-MM most recent month (default: last month)')
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    if args.start:
        start = args.start
    else:
        y, m = now.year, now.month - 1
        if m == 0:
            m, y = 12, y - 1
        start = f"{y:04d}-{m:02d}"
    total_bars = total_trades = total_days = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        for ym in month_range(start, args.months):
            for day in days_in_month(ym):
                zp = fetch_daily(day, tmpdir)
                if not zp:
                    continue
                bars, n = parse_bars(zp)
                for hour, b in sorted(bars.items()):
                    tot = b['buy_n'] + b['sell_n']
                    store_normalized('flow_bars', 'binance-archive', {
                        'venue': 'binance-archive', 'symbol': 'BTCUSDT',
                        'hour': hour,
                        'trade_buy_notional': round(b['buy_n'], 2),
                        'trade_sell_notional': round(b['sell_n'], 2),
                        'buy_count': b['buy_c'], 'sell_count': b['sell_c'],
                        'imbalance': round((b['buy_n'] - b['sell_n']) / tot, 4) if tot else None,
                        'open': b['o'], 'high': b['h'], 'low': b['l'], 'close': b['c'],
                        'source_url': f'{BASE_URL}/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-{day}.zip',
                        'source_role': 'history-backfill',
                    }, event_time=hour)
                os.remove(zp)  # keep tmp small; zip re-fetchable (backfillable truth)
                total_days += 1
                total_bars += len(bars)
                total_trades += n
                if total_days % 7 == 0:
                    print(f"  ... {total_days}d {len(bars)}h bars ({day})")
    print(f"[BTC BACKFILL] {total_days}d {total_bars} bars, {total_trades:,} trades at {utcnow()}")


if __name__ == '__main__':
    main()
