"""
2-year closes gap-fill — CoinGecko free caps at 365d (error 10012).

Fills pre-CG dates only (never overwrites CG rows):
  XMR: Kraken OHLC XXMRZUSD (721 daily candles, free, no key)
  BTC: Kraken OHLC XXBTZUSD (721 daily candles)
  QUBIC: Gate candlesticks QUBIC_USDT (2yr via from param)

Each row carries its source; seams are disclosed, not hidden.
CG remains the canonical last-365d source.

Usage:
    python3 scripts/load_closes_2y.py
    python3 scripts/load_closes_2y.py --coins XMR
"""

import argparse
import os
import sys
import glob
import json
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402


def existing_dates(sym):
    out = set()
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'price_history',
            f'chain={sym.lower()}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('date'):
                    out.add(r['date'])
    return out


def store(sym, date, close, volume, source):
    if not close or close <= 0:
        return False
    store_normalized('price_history', sym.lower(), {
        'symbol': sym, 'date': date,
        'exchange_time': date,
        'close_usd': close, 'volume_usd': volume,
        'source_role': 'gap-fill pre-CG (seam disclosed)',
        'source_id': source,
    }, event_time=date)
    return True


def load_kraken(sym, pair):
    have = existing_dates(sym)
    data = fetch_json('https://api.kraken.com/0/public/OHLC',
                      params={'pair': pair, 'interval': 1440},
                      source_id='kraken-ohlc', chain_id=sym.lower())
    if not isinstance(data, dict):
        print(f"  [{sym}] kraken fetch failed")
        return 0
    key = [k for k in (data.get('result') or {}) if k != 'last']
    rows = data['result'][key[0]] if key else []
    n = 0
    for r in rows:
        try:
            day = datetime.fromtimestamp(int(r[0]), tz=timezone.utc).strftime('%Y-%m-%d')
            close = float(r[4])
            vol = float(r[6]) * close if len(r) > 6 else None
        except (IndexError, ValueError, TypeError):
            continue
        if day not in have:
            n += store(sym, day, close, vol, 'kraken-ohlc')
    print(f"  [{sym}] kraken +{n} gap-fill closes ({len(rows)} candles scanned)")
    return n


def load_gate_qubic():
    have = existing_dates('QUBIC')
    data = fetch_json('https://api.gateio.ws/api/v4/spot/candlesticks',
                      params={'currency_pair': 'QUBIC_USDT', 'interval': '1d',
                              'limit': 1000, 'from': 1727049600},
                      source_id='gate-candles', chain_id='qubic')
    if not isinstance(data, list):
        print("  [QUBIC] gate fetch failed")
        return 0
    n = 0
    for r in data:
        try:
            day = datetime.fromtimestamp(int(r[0]), tz=timezone.utc).strftime('%Y-%m-%d')
            close = float(r[2])
            vol = float(r[1]) * close
        except (IndexError, ValueError, TypeError):
            continue
        if day not in have:
            n += store('QUBIC', day, close, vol, 'gate-candles')
    print(f"  [QUBIC] gate +{n} gap-fill closes ({len(data)} candles scanned)")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--coins', default='XMR,BTC,QUBIC')
    args = ap.parse_args()
    print(f"[2Y] {utcnow()}")
    total = 0
    for i, sym in enumerate([s.strip().upper() for s in args.coins.split(',')]):
        try:
            if sym == 'QUBIC':
                total += load_gate_qubic()
            elif sym == 'XMR':
                total += load_kraken('XMR', 'XMRUSD')
            elif sym == 'BTC':
                total += load_kraken('BTC', 'XBTUSD')
            else:
                print(f"  [{sym}] no 2yr source mapped")
        except Exception as e:
            print(f"  [{sym}] ERR {str(e)[:120]}")
        if i < len(args.coins.split(',')) - 1:
            time.sleep(5)
    print(f"[2Y] +{total} gap-fill closes")


if __name__ == '__main__':
    main()
