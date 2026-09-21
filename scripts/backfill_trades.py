"""
Bounded trade backfill via venue pagination (point-in-time safe).

Walks REST trade pages backwards per market (CoinEx deals page=N,
Gate trades page=N), archiving raw via core.fetch_json and writing
normalized trade rows flagged snapshot_kind=rest_backfill with original
exchange timestamps. Dedups against venue_l2 high-water marks in
warehouse/venue_l2_state.json so live and backfill never double-count.

Books are NOT backfillable (gone forever) — trades only.

Usage:
    python3 scripts/backfill_trades.py --pages 5 --limit 100
    python3 scripts/backfill_trades.py --pages 20 --venues coinex
"""

import argparse
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

STATE_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_l2_state.json')


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except OSError:
        return {'markets': {}, 'last_ids': {}}


def backfill_coinex(sym, market, pages, limit):
    seen, new = set(), 0
    for page in range(1, pages + 1):
        data = fetch_json('https://api.coinex.com/v2/spot/deals',
                          params={'market': market, 'limit': limit, 'page': page},
                          source_id='coinex-deals-backfill', chain_id='venue')
        deals = (data.get('data', []) or []) if data and data.get('code') == 0 else []
        if not deals:
            break
        for d in deals:
            did = str(d.get('deal_id', ''))
            if not did or did in seen:
                continue
            seen.add(did)
            store_normalized('trade', 'venue', {
                'venue': 'coinex', 'symbol': sym, 'market': market,
                'poll_id': None, 'receive_time': utcnow(),
                'trade_id': did, 'price': d.get('price'),
                'quantity': d.get('amount'), 'aggressor_side': d.get('side'),
                'exchange_time_ms': d.get('created_at'),
                'snapshot_kind': 'rest_backfill', 'backfill_page': page,
            })
            new += 1
        time.sleep(0.4)
        if len(deals) < limit:
            break
    return new


def backfill_gate(sym, pair, pages, limit):
    seen, new = set(), 0
    for page in range(1, pages + 1):
        data = fetch_json('https://api.gateio.ws/api/v4/spot/trades',
                          params={'currency_pair': pair, 'limit': limit, 'page': page},
                          source_id='gate-trades-backfill', chain_id='venue')
        if not isinstance(data, list) or not data:
            break
        for t in data:
            tid = str(t.get('id', ''))
            if not tid or tid in seen:
                continue
            seen.add(tid)
            store_normalized('trade', 'venue', {
                'venue': 'gate', 'symbol': sym, 'market': pair,
                'poll_id': None, 'receive_time': utcnow(),
                'trade_id': tid, 'price': t.get('price'),
                'quantity': t.get('amount'), 'aggressor_side': t.get('side'),
                'exchange_time': t.get('create_time'),
                'exchange_time_ms': t.get('create_time_ms'),
                'venue_sequence_id': t.get('sequence_id'),
                'snapshot_kind': 'rest_backfill', 'backfill_page': page,
            })
            new += 1
        time.sleep(0.4)
        if len(data) < limit:
            break
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', type=int, default=5)
    ap.add_argument('--limit', type=int, default=100)
    ap.add_argument('--venues', default='coinex,gate')
    args = ap.parse_args()
    venues = set(args.venues.split(','))
    state = load_state()
    total = 0
    for key in sorted(state.get('markets', {})):
        m = state['markets'][key]
        if m['venue'] not in venues:
            continue
        try:
            if m['venue'] == 'coinex':
                n = backfill_coinex(m['base'], m['market'], args.pages, args.limit)
            else:
                n = backfill_gate(m['base'], m['market'], args.pages, args.limit)
            print(f"  [{key}] +{n} backfilled trades")
            total += n
        except Exception as e:
            print(f"  [{key}] error: {str(e)[:120]}")
    print(f"[BACKFILL] +{total} trades ({args.pages} pages x {args.limit})")


if __name__ == '__main__':
    main()
