"""
Venue WS tick archiver — maximum-granularity market data (supplements REST).

CoinEx WS (wss://socket.coinex.com): depth.subscribe [market, 50, "0"] +
deals.subscribe [market]. Depth frames are full-book (is_full=true) or
deltas; deals carry ids + exchange timestamps.
Gate WS (wss://api.gateio.ws/ws/v4/): spot.order_book [pair, 50, "100ms"]
+ spot.trades [pair].

Every frame archived RAW before parsing. Trades → trade rows (dedup by
venue id). Books held in memory, emitted as orderbook_snapshot rows every
SNAPSHOT_EVERY seconds per market + on full refreshes. Reconnect with
backoff; REST poller (venue_l2) remains the gap-closing checkpoint layer.

Markets read from warehouse/venue_l2_state.json (discovery-owned).

Usage:
    python3 collectors/venue_ws.py            # daemon loop (supervised)
    python3 collectors/venue_ws.py --once 60  # capture 60s then exit
"""

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from core import _archive_raw, store_normalized
except ImportError:
    _archive_raw = store_normalized = None

try:
    import websockets
except ImportError:
    websockets = None

CX_URL = "wss://socket.coinex.com/"
GATE_URL = "wss://api.gateio.ws/ws/v4/"
STATE_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_l2_state.json')
PID_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_ws.pid')
HEARTBEAT_FILE = os.path.join(BASE_DIR, 'warehouse', 'venue_ws_heartbeat.json')
SNAPSHOT_EVERY = 10
BOOK_DEPTH = 50
RAW_BATCH = 200       # frames per raw file
RAW_FLUSH_SECS = 5.0  # or seconds, whichever first


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def load_markets():
    try:
        st = json.load(open(STATE_FILE))
    except OSError:
        return [], []
    cx = [m['market'] for k, m in st.get('markets', {}).items() if m.get('venue') == 'coinex']
    gate = [m['market'] for k, m in st.get('markets', {}).items() if m.get('venue') == 'gate']
    return sorted(set(cx)), sorted(set(gate))


def book_metrics(bids, asks):
    try:
        bb = float(bids[0][0]) if bids else None
        ba = float(asks[0][0]) if asks else None
        mid = (bb + ba) / 2 if bb and ba else None
        spread = (ba - bb) / mid * 10000 if mid else None
        bands = {}
        if mid:
            for bps in (10, 25, 50, 100, 500):
                lim = bps / 10000
                bn = sum(float(p) * float(q) for p, q in bids
                         if float(p) >= mid * (1 - lim))
                an = sum(float(p) * float(q) for p, q in asks
                         if float(p) <= mid * (1 + lim))
                bands[f'bid_{bps}bps'] = round(bn, 2)
                bands[f'ask_{bps}bps'] = round(an, 2)
        return mid, spread, bands
    except Exception:
        return None, None, {}


class TickArchiver:
    def __init__(self):
        self.running = False
        self.books = {}       # (venue, market) -> {'bids': {p: q}, 'asks': {p: q}}
        self.last_snap = {}
        self.seen_trades = set()
        self.stats = {'frames': 0, 'trades': 0, 'snapshots': 0, 'gaps': 0,
                      'reconnects': 0, 'errors': 0}
        self.last_ids = {}
        self._raw_buf = []
        self._raw_last_flush = time.time()

    def archive(self, venue, payload, kind, event_time=None):
        self.stats['frames'] += 1
        # Trades are low-volume: archive individually to keep per-row lineage.
        # Book frames are high-volume: batch them.
        if kind in ('deals', 'trades'):
            if _archive_raw is None:
                return None
            rt = utcnow()
            return _archive_raw(
                chain_id='venue', source_id=f'{venue}-ws', endpoint='ws-tick',
                event_time=event_time, observed_at=rt, response_received=rt,
                http_status=200, raw_body=json.dumps(payload, default=str),
                parsed_payload={'venue': venue, 'kind': kind},
                request_params={'venue': venue}, quality_flags=['ws', 'tick'])
        self._raw_buf.append({'venue': venue, 'kind': kind,
                              'event_time': event_time,
                              'received_at': utcnow(), 'payload': payload})
        if len(self._raw_buf) >= RAW_BATCH or \
                time.time() - self._raw_last_flush >= RAW_FLUSH_SECS:
            self.flush_raw()
        return None

    def flush_raw(self):
        if not self._raw_buf or _archive_raw is None:
            return None
        buf, self._raw_buf = self._raw_buf, []
        self._raw_last_flush = time.time()
        rt = utcnow()
        kinds = {}
        for e in buf:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
        return _archive_raw(
            chain_id='venue', source_id='venue-ws-batch', endpoint='ws-tick-batch',
            event_time=None, observed_at=buf[0]['received_at'],
            response_received=rt, http_status=200,
            raw_body=json.dumps(buf, default=str),
            parsed_payload={'frames': len(buf), 'kinds': kinds},
            request_params={'batch': True}, quality_flags=['ws', 'tick', 'batched'])

    def emit_trade(self, venue, market, symbol, tid, price, qty, side, et, raw_id):
        key = (venue, tid)
        if tid and key in self.seen_trades:
            return
        if tid:
            self.seen_trades.add(key)
            if len(self.seen_trades) > 20000:
                self.seen_trades = set(list(self.seen_trades)[-10000:])
        prev = self.last_ids.get((venue, market))
        if tid and prev:
            try:
                if int(tid) - int(prev) > 1:
                    self.stats['gaps'] += 1
                    if store_normalized:
                        store_normalized('gap_event', 'venue', {
                            'venue': venue, 'symbol': symbol, 'market': market,
                            'kind': 'ws_trade_id_jump', 'last_seen_id': prev,
                            'max_seen_id': tid})
            except (TypeError, ValueError):
                pass
        if tid:
            try:
                if prev is None or int(tid) > int(prev):
                    self.last_ids[(venue, market)] = tid
            except (TypeError, ValueError):
                self.last_ids[(venue, market)] = tid
        self.stats['trades'] += 1
        if store_normalized:
            store_normalized('trade', 'venue', {
                'venue': venue, 'symbol': symbol, 'market': market,
                'receive_time': utcnow(), 'exchange_time': et,
                'trade_id': tid, 'price': price, 'quantity': qty,
                'aggressor_side': side, 'snapshot_kind': 'ws_tick',
                'raw_event_id': raw_id})

    def apply_book(self, venue, market, symbol, bids, asks, is_full, raw_id, et=None):
        book = self.books.setdefault((venue, market),
                                     {'bids': {}, 'asks': {}})
        if is_full:
            book['bids'] = {p: q for p, q in bids}
            book['asks'] = {p: q for p, q in asks}
        else:
            for p, q in bids:
                if float(q) == 0:
                    book['bids'].pop(p, None)
                else:
                    book['bids'][p] = q
            for p, q in asks:
                if float(q) == 0:
                    book['asks'].pop(p, None)
                else:
                    book['asks'][p] = q
        now = time.time()
        if is_full or now - self.last_snap.get((venue, market), 0) >= SNAPSHOT_EVERY:
            self.last_snap[(venue, market)] = now
            sb = sorted(book['bids'].items(), key=lambda x: -float(x[0]))[:BOOK_DEPTH]
            sa = sorted(book['asks'].items(), key=lambda x: float(x[0]))[:BOOK_DEPTH]
            bids_l = [[p, q] for p, q in sb]
            asks_l = [[p, q] for p, q in sa]
            mid, spread, bands = book_metrics(bids_l, asks_l)
            self.stats['snapshots'] += 1
            if store_normalized:
                store_normalized('orderbook_snapshot', 'venue', {
                    'venue': venue, 'symbol': symbol, 'market': market,
                    'receive_time': utcnow(), 'exchange_time': et,
                    'mid': mid, 'spread_bps': spread, **bands,
                    'bid_levels': len(sb), 'ask_levels': len(sa),
                    'bids': bids_l, 'asks': asks_l,
                    'snapshot_kind': 'ws_snapshot' if is_full else 'ws_tick',
                    'raw_event_id': raw_id, 'source_role': 'raw_venue'})

    # -- CoinEx --
    async def run_coinex(self, markets):
        backoff = 5
        sym_of = {m: m.replace('USDT', '') for m in markets}
        while self.running:
            try:
                async with websockets.connect(CX_URL, open_timeout=15,
                                              ping_interval=20) as ws:
                    rid = 1
                    for m in markets:
                        await ws.send(json.dumps(
                            {"method": "depth.subscribe",
                             "params": [m, BOOK_DEPTH, "0"], "id": rid}))
                        rid += 1
                    for m in markets:
                        await ws.send(json.dumps(
                            {"method": "deals.subscribe",
                             "params": [m], "id": rid}))
                        rid += 1
                    print(f"[WS coinex] subscribed {len(markets)} markets")
                    backoff = 5
                    async for raw in ws:
                        if not self.running:
                            return
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        if 'method' not in msg:
                            continue
                        method = msg['method']
                        if method == 'depth.update':
                            full, book = msg['params'][0], msg['params'][1]
                            market = book.get('market') or ''
                            sym = sym_of.get(market, market.replace('USDT', ''))
                            raw_id = self.archive('coinex', msg, 'depth')
                            self.apply_book('coinex', market, sym,
                                            book.get('bids', []), book.get('asks', []),
                                            bool(full), raw_id)
                        elif method == 'deals.update':
                            market, deals = msg['params'][0], msg['params'][1]
                            sym = sym_of.get(market, market.replace('USDT', ''))
                            raw_id = self.archive('coinex', msg, 'deals')
                            for d in deals:
                                self.emit_trade(
                                    'coinex', market, sym, str(d.get('id')),
                                    d.get('price'), d.get('amount'),
                                    d.get('type'),
                                    datetime.fromtimestamp(
                                        float(d.get('time', 0)),
                                        tz=timezone.utc).isoformat()
                                    if d.get('time') else None, raw_id)
            except Exception as e:
                self.stats['reconnects'] += 1
                print(f"[WS coinex] {type(e).__name__}: {str(e)[:120]} — retry {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)

    # -- Gate --
    async def run_gate(self, pairs):
        backoff = 5
        sym_of = {p: p.split('_')[0] for p in pairs}
        while self.running:
            try:
                async with websockets.connect(GATE_URL, open_timeout=15,
                                              ping_interval=20) as ws:
                    for p in pairs:
                        await ws.send(json.dumps(
                            {"time": 0, "channel": "spot.order_book",
                             "event": "subscribe", "payload": [p, "50", "100ms"]}))
                    for p in pairs:
                        await ws.send(json.dumps(
                            {"time": 0, "channel": "spot.trades",
                             "event": "subscribe", "payload": [p]}))
                    print(f"[WS gate] subscribed {len(pairs)} markets")
                    backoff = 5
                    async for raw in ws:
                        if not self.running:
                            return
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        chan = msg.get('channel', '')
                        if msg.get('event') == 'subscribe':
                            continue
                        if chan == 'spot.trades':
                            res = msg.get('result', {})
                            pair = res.get('currency_pair', '')
                            sym = sym_of.get(pair, pair.split('_')[0])
                            raw_id = self.archive('gate', msg, 'trades',
                                                  res.get('create_time'))
                            self.emit_trade(
                                'gate', pair, sym, str(res.get('id', '')),
                                res.get('price'), res.get('amount'),
                                res.get('side'), res.get('create_time'),
                                raw_id)
                        elif chan == 'spot.order_book':
                            res = msg.get('result', {})
                            pair = res.get('s', '') or res.get('currency_pair', '')
                            sym = sym_of.get(pair, pair.split('_')[0])
                            raw_id = self.archive('gate', msg, 'depth')
                            self.apply_book(
                                'gate', pair, sym, res.get('bids', []),
                                res.get('asks', []),
                                bool(res.get('snapshot', False)), raw_id)
            except Exception as e:
                self.stats['reconnects'] += 1
                print(f"[WS gate] {type(e).__name__}: {str(e)[:120]} — retry {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)

    async def heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(30)
            self.flush_raw()
            try:
                with open(HEARTBEAT_FILE, 'w') as f:
                    json.dump({'heartbeat_at': utcnow(), 'mode': 'ws-daemon',
                               **self.stats}, f, indent=2, default=str)
            except Exception:
                pass

    async def run(self, duration=None):
        cx, gate = load_markets()
        print(f"[VENUE_WS] coinex={len(cx)} gate={len(gate)}")
        self.running = True
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        tasks = [asyncio.create_task(self.heartbeat_loop())]
        if cx:
            tasks.append(asyncio.create_task(self.run_coinex(cx)))
        if gate:
            tasks.append(asyncio.create_task(self.run_gate(gate)))
        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                await asyncio.gather(*tasks)
        finally:
            self.running = False
            try:
                self.flush_raw()
            except Exception:
                pass
            for t in tasks:
                t.cancel()
            try:
                os.remove(PID_FILE)
            except OSError:
                pass


def main():
    global websockets
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', type=int, default=None)
    args = ap.parse_args()
    if websockets is None:
        print("[FATAL] websockets lib missing — use powpowpow venv")
        sys.exit(1)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: sys.exit(0))
    asyncio.run(TickArchiver().run(duration=args.once))


if __name__ == '__main__':
    main()
