"""
Venue L2 Archival — autonomous multi-venue order-book + trade collection.

Garden role: continuous L2 state for every tracked market on every reachable
venue. Every HTTP response is auto-archived RAW via core.fetch_json BEFORE
parsing (moat rule). Normalized rows carry receive_time, poll_id, venue,
and lineage. Gaps are recorded as events, never silently skipped.

Venues: CoinEx + Gate.io (public endpoints, no auth).
SafeTrade has its own collector (collectors/l2_archival.py) — staged until
egress unblocks; this module keeps the moat clock running meanwhile.

Universe: static V1 list + autonomous discovery (new USDT listings of
tracked symbols are picked up hourly; delistings logged as events).

Usage:
    python3 collectors/venue_l2.py --once          # single pass (test/cron)
    python3 collectors/venue_l2.py                 # daemon loop (supervised)
    python3 collectors/venue_l2.py --cadence 30    # book poll seconds
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

UNIVERSE = ['PRL', 'QUBIC', 'XMR', 'KAS', 'NOCK', 'XEL', 'XTM', 'NOS', 'AKT',
            'QUAN', 'CLORE', 'TAO', 'FLUX', 'TSC', 'GNK']

STATE_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_l2_state.json')
PID_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_l2.pid')
HEARTBEAT_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_l2_heartbeat.json')

RUNNING = True


def handle_signal(sig, frame):
    global RUNNING
    RUNNING = False


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'markets': {}, 'last_ids': {}, 'poll_id': 0, 'universe_events': []}


def save_state(state):
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2, default=str)
    os.replace(tmp, STATE_FILE)


def write_heartbeat(stats):
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            json.dump({'heartbeat_at': utcnow(), **stats}, f, indent=2, default=str)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Discovery (archived raw; re-run hourly for autonomous listing detection)
# ---------------------------------------------------------------------------

def discover_coinex():
    data = fetch_json('https://api.coinex.com/v2/spot/market',
                      source_id='coinex-market-list', chain_id='venue')
    markets = {}
    if data and isinstance(data.get('data'), list):
        for m in data['data']:
            base = (m.get('base_ccy') or '').upper()
            if base in UNIVERSE and m.get('quote_ccy') == 'USDT':
                markets[base] = {'venue': 'coinex', 'market': m.get('market'),
                                 'base': base, 'quote': 'USDT'}
    return markets


def discover_gate():
    data = fetch_json('https://api.gateio.ws/api/v4/spot/currency_pairs',
                      source_id='gate-pairs-list', chain_id='venue')
    markets = {}
    if isinstance(data, list):
        for p in data:
            base = (p.get('base') or '').upper()
            if base in UNIVERSE and p.get('quote') == 'USDT' \
                    and p.get('trade_status') == 'tradable':
                markets[base] = {'venue': 'gate', 'market': p.get('id'),
                                 'base': base, 'quote': 'USDT'}
    return markets


def refresh_universe(state):
    """Re-discover; log listings/delistings as universe events (survivor-bias log)."""
    found = {}
    for venue, fn in (('coinex', discover_coinex), ('gate', discover_gate)):
        try:
            for sym, m in fn().items():
                found.setdefault(sym, {})[venue] = m
        except Exception as e:
            print(f"  [DISCOVER {venue}] error: {e}")
        time.sleep(1)
    prev = state.get('markets', {})
    for sym, venues in found.items():
        for venue in venues:
            key = f'{venue}:{sym}'
            if key not in prev:
                ev = {'at': utcnow(), 'type': 'market_listed',
                      'venue': venue, 'symbol': sym, 'detail': venues[venue]}
                state['universe_events'].append(ev)
                store_normalized('universe_event', 'venue', ev)
                print(f"  [UNIVERSE] NEW listing: {key}")
    for key in prev:
        if key not in {f'{v}:{s}' for s, vs in found.items() for v in vs}:
            ev = {'at': utcnow(), 'type': 'market_missing',
                  'venue_symbol': key}
            state['universe_events'].append(ev)
            store_normalized('universe_event', 'venue', ev)
            print(f"  [UNIVERSE] MISSING (delisted?): {key}")
    state['markets'] = {f'{v}:{s}': m for s, vs in found.items() for v, m in vs.items()}
    state['last_discovery'] = utcnow()
    return state


# ---------------------------------------------------------------------------
# Polls
# ---------------------------------------------------------------------------

def book_stats(bids, asks):
    try:
        bb = float(bids[0][0]) if bids else None
        ba = float(asks[0][0]) if asks else None
        mid = (bb + ba) / 2 if bb and ba else None
        spread_bps = (ba - bb) / mid * 10000 if mid else None
        bid_n = sum(float(p) * float(q) for p, q in bids[:20])
        ask_n = sum(float(p) * float(q) for p, q in asks[:20])
        return mid, spread_bps, bid_n, ask_n
    except Exception:
        return None, None, None, None


def poll_coinex_book(sym, market, poll_id, receive_time):
    data = fetch_json('https://api.coinex.com/v2/spot/depth',
                      params={'market': market, 'limit': 20, 'interval': '0'},
                      source_id='coinex-depth', chain_id='venue')
    if not data or data.get('code') != 0:
        return False
    d = data.get('data', {}) or {}
    bids, asks = d.get('bids', []), d.get('asks', [])
    mid, spread_bps, bid_n, ask_n = book_stats(bids, asks)
    store_normalized('orderbook_snapshot', 'venue', {
        'venue': 'coinex', 'symbol': sym, 'market': market,
        'poll_id': poll_id, 'receive_time': receive_time,
        'mid': mid, 'spread_bps': spread_bps,
        'bid_notional_20': bid_n, 'ask_notional_20': ask_n,
        'bids': bids[:20], 'asks': asks[:20],
        'snapshot_kind': 'rest_poll', 'source_role': 'raw_venue',
    })
    return True


def poll_coinex_ticker(sym, market, poll_id, receive_time):
    data = fetch_json('https://api.coinex.com/v2/spot/ticker',
                      params={'market': market},
                      source_id='coinex-ticker', chain_id='venue')
    if not data or data.get('code') != 0:
        return False
    rows = data.get('data', []) or []
    if rows:
        t = rows[0]
        store_normalized('ticker', 'venue', {
            'venue': 'coinex', 'symbol': sym, 'market': market,
            'poll_id': poll_id, 'receive_time': receive_time,
            'last': t.get('last'), 'open': t.get('open'),
            'high': t.get('high'), 'low': t.get('low'),
            'volume': t.get('volume'), 'value': t.get('value'),
            'volume_buy': t.get('volume_buy'), 'volume_sell': t.get('volume_sell'),
        })
    return True


def poll_coinex_deals(sym, market, poll_id, state):
    data = fetch_json('https://api.coinex.com/v2/spot/deals',
                      params={'market': market, 'limit': 100},
                      source_id='coinex-deals', chain_id='venue')
    if not data or data.get('code') != 0:
        return 0
    deals = data.get('data', []) or []
    key = f'coinex:{sym}'
    last_id = state['last_ids'].get(key, 0)
    new = 0
    max_id = last_id
    for d in deals:
        try:
            did = int(d.get('deal_id', 0))
        except (TypeError, ValueError):
            continue
        max_id = max(max_id, did)
        if did > last_id:
            store_normalized('trade', 'venue', {
                'venue': 'coinex', 'symbol': sym, 'market': market,
                'poll_id': poll_id, 'receive_time': utcnow(),
                'trade_id': str(did), 'price': d.get('price'),
                'quantity': d.get('amount'), 'aggressor_side': d.get('side'),
                'exchange_time_ms': d.get('created_at'),
            })
            new += 1
    if last_id and deals and (max_id - last_id) > (new + 5):
        # ids jumped beyond what one page explains → likely missed trades
        store_normalized('gap_event', 'venue', {
            'venue': 'coinex', 'symbol': sym, 'market': market,
            'poll_id': poll_id, 'kind': 'deal_id_jump',
            'last_seen_id': last_id, 'max_seen_id': max_id,
            'new_in_page': new,
        })
    state['last_ids'][key] = max_id
    return new


def poll_gate_book(sym, pair, poll_id, receive_time):
    data = fetch_json('https://api.gateio.ws/api/v4/spot/order_book',
                      params={'currency_pair': pair, 'limit': 20},
                      source_id='gate-book', chain_id='venue')
    if not isinstance(data, dict) or 'bids' not in data:
        return False
    bids, asks = data.get('bids', []), data.get('asks', [])
    mid, spread_bps, bid_n, ask_n = book_stats(bids, asks)
    store_normalized('orderbook_snapshot', 'venue', {
        'venue': 'gate', 'symbol': sym, 'market': pair,
        'poll_id': poll_id, 'receive_time': receive_time,
        'mid': mid, 'spread_bps': spread_bps,
        'bid_notional_20': bid_n, 'ask_notional_20': ask_n,
        'bids': bids[:20], 'asks': asks[:20],
        'venue_update_id': data.get('update'), 'venue_current': data.get('current'),
        'snapshot_kind': 'rest_poll', 'source_role': 'raw_venue',
    })
    return True


def poll_gate_ticker(sym, pair, poll_id, receive_time):
    data = fetch_json('https://api.gateio.ws/api/v4/spot/tickers',
                      params={'currency_pair': pair},
                      source_id='gate-ticker', chain_id='venue')
    if not isinstance(data, list) or not data:
        return False
    t = data[0]
    store_normalized('ticker', 'venue', {
        'venue': 'gate', 'symbol': sym, 'market': pair,
        'poll_id': poll_id, 'receive_time': receive_time,
        'last': t.get('last'), 'lowest_ask': t.get('lowest_ask'),
        'highest_bid': t.get('highest_bid'), 'base_volume': t.get('base_volume'),
        'quote_volume': t.get('quote_volume'),
        'high_24h': t.get('high_24h'), 'low_24h': t.get('low_24h'),
    })
    return True


def poll_gate_trades(sym, pair, poll_id, state):
    data = fetch_json('https://api.gateio.ws/api/v4/spot/trades',
                      params={'currency_pair': pair, 'limit': 100},
                      source_id='gate-trades', chain_id='venue')
    if not isinstance(data, list):
        return 0
    key = f'gate:{sym}'
    last_id = state['last_ids'].get(key, '')
    new = 0
    max_id = last_id
    for t in data:
        tid = str(t.get('id', ''))
        if max_id == '' or (tid.isdigit() and max_id.isdigit() and int(tid) > int(max_id)) \
                or (not tid.isdigit() and tid > str(max_id)):
            max_id = tid
        if last_id == '' or tid > str(last_id):
            # first run: record high-water mark without backfilling history
            if last_id != '':
                store_normalized('trade', 'venue', {
                    'venue': 'gate', 'symbol': sym, 'market': pair,
                    'poll_id': poll_id, 'receive_time': utcnow(),
                    'trade_id': tid, 'price': t.get('price'),
                    'quantity': t.get('amount'), 'aggressor_side': t.get('side'),
                    'exchange_time': t.get('create_time'),
                    'exchange_time_ms': t.get('create_time_ms'),
                    'venue_sequence_id': t.get('sequence_id'),
                })
                new += 1
    if last_id == '':
        state['last_ids'][key] = max_id  # baseline, no backfill
    else:
        try:
            if int(max_id) - int(last_id) > new + 5:
                store_normalized('gap_event', 'venue', {
                    'venue': 'gate', 'symbol': sym, 'market': pair,
                    'poll_id': poll_id, 'kind': 'trade_id_jump',
                    'last_seen_id': last_id, 'max_seen_id': max_id,
                    'new_in_page': new,
                })
        except (TypeError, ValueError):
            pass
        state['last_ids'][key] = max_id
    return new


# ---------------------------------------------------------------------------
# Pass + loop
# ---------------------------------------------------------------------------

def run_pass(state, cadence_note=''):
    state['poll_id'] += 1
    poll_id = state['poll_id']
    t0 = time.time()
    stats = {'books': 0, 'tickers': 0, 'trades': 0, 'errors': 0}
    for key in sorted(state.get('markets', {})):
        if not RUNNING:
            break
        m = state['markets'][key]
        rt = utcnow()
        try:
            if m['venue'] == 'coinex':
                if poll_coinex_book(m['base'], m['market'], poll_id, rt):
                    stats['books'] += 1
                time.sleep(0.3)
                if poll_coinex_ticker(m['base'], m['market'], poll_id, rt):
                    stats['tickers'] += 1
                time.sleep(0.3)
                stats['trades'] += poll_coinex_deals(m['base'], m['market'], poll_id, state)
            else:
                if poll_gate_book(m['base'], m['market'], poll_id, rt):
                    stats['books'] += 1
                time.sleep(0.3)
                if poll_gate_ticker(m['base'], m['market'], poll_id, rt):
                    stats['tickers'] += 1
                time.sleep(0.3)
                stats['trades'] += poll_gate_trades(m['base'], m['market'], poll_id, state)
        except Exception as e:
            stats['errors'] += 1
            print(f"  [{key}] error: {str(e)[:120]}")
        time.sleep(0.4)
    dt = time.time() - t0
    print(f"[PASS {poll_id}] markets={len(state['markets'])} books={stats['books']} "
          f"tickers={stats['tickers']} new_trades={stats['trades']} "
          f"errors={stats['errors']} {dt:.1f}s {cadence_note}")
    return stats


def main():
    global RUNNING
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--cadence', type=int, default=30)
    args = ap.parse_args()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    state = load_state()
    if not state.get('markets') or \
            (time.time() - os.path.getmtime(STATE_FILE) if os.path.exists(STATE_FILE) else 1e9) > 3600:
        print("[DISCOVERY] refreshing market universe...")
        state = refresh_universe(state)
        save_state(state)
    print(f"[VENUE_L2] tracking {len(state['markets'])} markets: "
          f"{sorted(state['markets'])[:12]}")

    if args.once:
        stats = run_pass(state)
        save_state(state)
        write_heartbeat({**stats, 'mode': 'once',
                         'markets': len(state['markets'])})
        return

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(f"[VENUE_L2] daemon loop, book cadence={args.cadence}s pid={os.getpid()}")
    last_discovery = time.time()
    try:
        while RUNNING:
            if time.time() - last_discovery > 3600:
                state = refresh_universe(state)
                last_discovery = time.time()
            stats = run_pass(state)
            save_state(state)
            write_heartbeat({**stats, 'mode': 'daemon',
                             'markets': len(state['markets']),
                             'poll_id': state['poll_id']})
            for _ in range(args.cadence):
                if not RUNNING:
                    break
                time.sleep(1)
    finally:
        save_state(state)
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        print("[VENUE_L2] stopped")


if __name__ == '__main__':
    main()
