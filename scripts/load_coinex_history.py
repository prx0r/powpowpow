"""
CoinEx daily klines — venue-native OHLCV for XMR/QUBIC/BTC.

Free, no key, limit=1000 (~2.7yr) per call. Venue-native closes let
the garden measure venue-vs-index basis (redundant observation,
todo #7): same date, CG close vs CoinEx close, disagreements kept.

Rows carry source coinex-klines; consumers needing a single series
filter by source_id. No overwrites, no merges.

Usage:
    python3 scripts/load_coinex_history.py
    python3 scripts/load_coinex_history.py --coins XMR
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

MARKETS = {'XMR': 'XMRUSDT', 'QUBIC': 'QUBICUSDT', 'BTC': 'BTCUSDT'}


def load_coin(sym, market):
    data = fetch_json(
        'https://api.coinex.com/v2/spot/kline',
        params={'market': market, 'period': '1day', 'limit': 1000},
        source_id='coinex-klines', chain_id=sym.lower())
    rows = (data or {}).get('data', []) if isinstance(data, dict) else []
    n = 0
    for r in rows:
        try:
            day = datetime.fromtimestamp(int(r['created_at']) / 1000,
                                         tz=timezone.utc).strftime('%Y-%m-%d')
            close = float(r['close'])
        except (KeyError, ValueError, TypeError):
            continue
        if not close:
            continue
        store_normalized('price_history', sym.lower(), {
            'symbol': sym, 'date': day,
            'exchange_time': datetime.fromtimestamp(
                int(r['created_at']) / 1000, tz=timezone.utc).isoformat(),
            'close_usd': close,
            'open_usd': float(r.get('open') or 0) or None,
            'high_usd': float(r.get('high') or 0) or None,
            'low_usd': float(r.get('low') or 0) or None,
            'volume_base': float(r.get('volume') or 0) or None,
            'volume_usd': float(r.get('value') or 0) or None,
            'source_role': 'venue-native OHLCV (basis vs index)',
            'source_id': 'coinex-klines',
        }, event_time=day)
        n += 1
    print(f"  [{sym}] +{n} venue closes")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--coins', default='XMR,QUBIC,BTC')
    args = ap.parse_args()
    print(f"[COINEX] {utcnow()}")
    total = 0
    coins = [s.strip().upper() for s in args.coins.split(',')]
    for i, sym in enumerate(coins):
        if sym not in MARKETS:
            print(f"  [{sym}] no coinex market mapped")
            continue
        try:
            total += load_coin(sym, MARKETS[sym])
        except Exception as e:
            print(f"  [{sym}] ERR {str(e)[:120]}")
        if i < len(coins) - 1:
            time.sleep(5)
    print(f"[COINEX] +{total} venue rows")


if __name__ == '__main__':
    main()
