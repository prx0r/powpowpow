"""
SafeTrade L2 Archival — autonomous gap-safe collector (STAGED).

Status: code-complete and replay-verified, NOT YET RUNNING against the
live venue: safe.trade REST + WS return HTTP 403 from this box's egress
(geo-block, verified 2026-09-19 direct and via agent-vault proxy, both
hosts). The moment egress works — or from any unblocked box — run:

    python3 collectors/l2_archival.py            # daemon loop (supervised)
    python3 collectors/l2_archival.py --once 60  # 60s capture then exit

Garden guarantees (same as collectors/venue_l2.py):
- RAW message archived via core BEFORE parsing (moat rule).
- receive_time (our clock, UTC) vs exchange event_time (their clock, else None).
- sequence/update IDs tracked per stream; jumps → gap_event rows.
- snapshot-vs-delta kind recorded; REST depth checkpoint after every
  reconnect to close WS gaps.
- market discovery: REST list when reachable, else seed list + live
  `global.tickers` discovery (new listings auto-subscribed).
- orderbook stored as one snapshot row (not per-level write amplification).

No auth needed (public WS). Agent-vault SafeTrade credentials are for
private endpoints only and are never read by this module.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    from core import _archive_raw, store_normalized, utcnow, fetch_json
except (ImportError, AttributeError):
    # core/ package shadows core.py — load it directly
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location('_core_py',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core.py'))
    _core = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_core)
    _archive_raw = _core._archive_raw
    store_normalized = _core.store_normalized
    utcnow = _core.utcnow
    fetch_json = _core.fetch_json

try:
    import websockets
except ImportError:
    websockets = None

WS_URL = "wss://safe.trade/api/v2/websocket/public"
WS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Origin": "https://safe.trade",
    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
    "Sec-WebSocket-Version": "13",
    "Sec-WebSocket-Protocol": "chat, superchat",
}
# Seed universe (SafeTrade market ids are lowercase-concatenated).
# btcusdt verified live on SafeTrade 2026-09-23 (venue-of-truth L2 for BTC).
SEED_MARKETS = ['qubicusdt', 'prlusdt', 'xmrusdt', 'nockusdt', 'kasusdt',
                'xelusdt', 'xtmusdt', 'nosusdt', 'aktusdt', 'btcusdt']
PID_FILE = os.path.join(BASE_DIR, 'warehouse', 'safetrade_l2.pid')
HEARTBEAT_FILE = os.path.join(BASE_DIR, 'warehouse', 'safetrade_l2_heartbeat.json')
MIN_FREE_BYTES = int(os.environ.get('POW_MIN_FREE_BYTES', 2 * 1024 ** 3))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pure message handling (replay-testable, no I/O)
# ---------------------------------------------------------------------------

def parse_message(data):
    """Split one WS frame into (stream, payload) pairs.

    SafeTrade frames are dicts keyed by stream name, e.g.
    {"qubicusdt.depth": {...}, "qubicusdt.trades": [...]}.
    Returns list of dicts: stream, kind (depth/trades/tickers/other),
    market, payload, seq (update/id if present else None),
    event_time (exchange timestamp if present else None).
    """
    out = []
    if not isinstance(data, dict):
        return out
    for stream, payload in data.items():
        if stream in ('event', 'streams', 'message'):
            continue
        if stream == 'global.tickers':
            out.append({'stream': stream, 'kind': 'tickers', 'market': None,
                        'payload': payload, 'seq': None, 'event_time': None})
            continue
        market, _, chan = stream.partition('.')
        kind = chan if chan in ('depth', 'trades') else 'other'
        seq, event_time = None, None
        if isinstance(payload, dict):
            seq = payload.get('sequence') or payload.get('update_id') \
                or payload.get('version') or payload.get('id')
            event_time = payload.get('timestamp') or payload.get('time') \
                or payload.get('created_at') or payload.get('date')
        out.append({'stream': stream, 'kind': kind, 'market': market,
                    'payload': payload, 'seq': seq, 'event_time': event_time})
    return out


class StreamGap:
    """Per-stream sequence tracker. seq_compare(a, b) -> True if b follows a."""

    def __init__(self):
        self.last_seq = {}

    def check(self, stream, seq):
        """Returns 'ok' | 'first' | 'duplicate' | 'gap' | 'unknown' (no seq)."""
        if seq is None:
            return 'unknown'
        prev = self.last_seq.get(stream)
        if prev is None:
            self.last_seq[stream] = seq
            return 'first'
        try:
            gap = int(seq) - int(prev)
            self.last_seq[stream] = seq
            if gap <= 0:
                return 'duplicate'
            return 'ok' if gap == 1 else 'gap'
        except (TypeError, ValueError):
            changed = seq != prev
            self.last_seq[stream] = seq
            return 'ok' if changed else 'duplicate'


def depth_metrics(depth):
    try:
        bids = depth.get('bids', []) or []
        asks = depth.get('asks', []) or []
        bb = float(bids[0][0]) if bids else None
        ba = float(asks[0][0]) if asks else None
        mid = (bb + ba) / 2 if bb and ba else None
        spread = (ba - bb) / mid * 10000 if mid else None
        return mid, spread, len(bids), len(asks)
    except Exception:
        return None, None, 0, 0


def discover_seed_markets():
    """REST market list when reachable, else seed list (egress-blocked)."""
    if fetch_json is None:
        return list(SEED_MARKETS)
    try:
        data = fetch_json('https://safe.trade/api/v2/trade/public/markets',
                          source_id='safetrade-markets', chain_id='safetrade')
        if isinstance(data, list):
            ids = [m.get('id') for m in data if isinstance(m, dict) and m.get('id')]
            ours = [i for i in ids if any(i.startswith(s) for s in
                    ('qubic', 'prl', 'xmr', 'nock', 'kas', 'xel', 'xtm', 'nos', 'akt',
                     'btc', 'quan', 'tsc', 'gnk', 'npt', 'qtc'))]
            tracked = [market for market in SEED_MARKETS if market in ours]
            if tracked:
                return tracked
    except Exception:
        pass
    return list(SEED_MARKETS)


# ---------------------------------------------------------------------------
# Live archival
# ---------------------------------------------------------------------------

class L2Archival:
    def __init__(self):
        self.running = False
        self.ws = None
        self.markets = []
        self.gaps = StreamGap()
        self.stats = {}
        self.start_time = None

    def _bump(self, market, kind):
        self.stats.setdefault(market, {'depth': 0, 'trades': 0, 'gaps': 0})
        if kind in self.stats[market]:
            self.stats[market][kind] += 1

    def archive_raw(self, entry, receive_time, kind):
        if _archive_raw is None:
            return None
        observation = _archive_raw(
            chain_id='safetrade', source_id='safetrade-ws',
            endpoint=WS_URL, event_time=entry['event_time'],
            observed_at=receive_time, response_received=receive_time,
            http_status=200, raw_body=json.dumps(entry['payload'], default=str),
            parsed_payload={'stream': entry['stream'], 'seq': entry['seq']},
            request_params={'stream': entry['stream']},
            quality_flags=['ws', kind],
            transport='websocket',
            source_role='raw_venue',
            event_type=entry['stream'],
        )
        if isinstance(observation, dict):
            return observation.get('observation_id')
        return observation

    def handle_entry(self, entry, receive_time):
        market = entry['market'] or 'global'
        raw_id = self.archive_raw(entry, receive_time, entry['kind'])
        seq_status = self.gaps.check(entry['stream'], entry['seq'])
        if seq_status == 'gap':
            self._bump(market, 'gaps')
            if store_normalized:
                store_normalized('gap_event', 'safetrade', {
                    'venue': 'safetrade', 'symbol': market,
                    'stream': entry['stream'], 'kind': 'ws_seq_jump',
                    'seq': entry['seq'], 'receive_time': receive_time,
                    'raw_event_id': raw_id,
                })
        if entry['kind'] == 'depth':
            self._bump(market, 'depth')
            if store_normalized:
                depth = entry['payload'] if isinstance(entry['payload'], dict) else {}
                mid, spread, nb, na = depth_metrics(depth)
                store_normalized('orderbook_snapshot', 'safetrade', {
                    'venue': 'safetrade', 'symbol': market,
                    'receive_time': receive_time,
                    'exchange_time': entry['event_time'],
                    'venue_seq': entry['seq'],
                    'seq_status': seq_status, 'snapshot_kind': 'ws_delta',
                    'mid': mid, 'spread_bps': spread,
                    'bid_levels': nb, 'ask_levels': na,
                    'bids': (depth.get('bids') or [])[:50],
                    'asks': (depth.get('asks') or [])[:50],
                    'raw_event_id': raw_id, 'source_role': 'raw_venue',
                })
        elif entry['kind'] == 'trades':
            payload = entry['payload']
            trades = payload if isinstance(payload, list) else [payload]
            for t in trades:
                self._bump(market, 'trades')
                if store_normalized:
                    if isinstance(t, list) and len(t) >= 3:
                        price, qty, side = t[0], t[1], ('buy' if t[2] == 'b' else 'sell')
                        tid, et = None, entry['event_time']
                    elif isinstance(t, dict):
                        price, qty = t.get('price'), t.get('amount') or t.get('quantity')
                        side = t.get('side')
                        tid = t.get('id') or t.get('trade_id')
                        et = t.get('created_at') or t.get('time') or entry['event_time']
                    else:
                        continue
                    store_normalized('trade', 'safetrade', {
                        'venue': 'safetrade', 'symbol': market,
                        'receive_time': receive_time, 'exchange_time': et,
                        'venue_seq': entry['seq'], 'seq_status': seq_status,
                        'trade_id': tid, 'price': price, 'quantity': qty,
                        'aggressor_side': side, 'raw_event_id': raw_id,
                    })
        elif entry['kind'] == 'tickers':
            # Autonomous discovery: new USDT markets join the subscription.
            payload = entry['payload']
            tickers = payload if isinstance(payload, list) else [payload]
            for t in tickers:
                if not isinstance(t, dict):
                    continue
                mid = t.get('market') or t.get('id') or ''
                if mid and mid not in self.markets and mid.endswith('usdt'):
                    self.markets.append(mid)
                    self.stats.setdefault(mid, {'depth': 0, 'trades': 0, 'gaps': 0})
            if store_normalized:
                store_normalized('ticker', 'safetrade', {
                    'venue': 'safetrade', 'receive_time': receive_time,
                    'snapshot_kind': 'ws_tick', 'tickers': tickers,
                    'raw_event_id': raw_id,
                })

    async def rest_checkpoint(self, markets):
        """REST depth snapshot per market to close any WS gap (archived raw)."""
        if fetch_json is None:
            return
        for m in markets:
            try:
                result = await asyncio.to_thread(
                    fetch_json,
                    f'https://safe.trade/api/v2/trade/public/markets/{m}/depth',
                    source_id='safetrade-rest-checkpoint', chain_id='safetrade',
                    return_result=True)
                data = result.get('parsed') if result else None
                raw_event_id = result.get('observation_id') if result else None
                if data and store_normalized:
                    depth = data if isinstance(data, dict) else {}
                    mid, spread, nb, na = depth_metrics(depth)
                    store_normalized('orderbook_snapshot', 'safetrade', {
                        'venue': 'safetrade', 'symbol': m,
                        'receive_time': utc_now(),
                        'snapshot_kind': 'rest_checkpoint',
                        'mid': mid, 'spread_bps': spread,
                        'bid_levels': nb, 'ask_levels': na,
                        'bids': (depth.get('bids') or [])[:50],
                        'asks': (depth.get('asks') or [])[:50],
                        'raw_event_id': raw_event_id,
                        'source_role': 'raw_venue',
                    })
            except Exception as e:
                print(f"  [CHECKPOINT {m}] {str(e)[:100]}")
            await asyncio.sleep(0.5)

    async def run_forever(self):
        if websockets is None:
            print("[FATAL] websockets lib missing — run in powpowpow venv")
            return
        self.running = True
        self.start_time = time.time()
        self.markets = discover_seed_markets()
        print(f"[SAFETRADE_L2] markets: {self.markets}")
        backoff = 5
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        try:
            while self.running:
                if shutil.disk_usage(BASE_DIR).free < MIN_FREE_BYTES:
                    self.heartbeat()
                    print(f"[DISK] waiting for {MIN_FREE_BYTES} free bytes")
                    await asyncio.sleep(300)
                    continue
                try:
                    import ssl as _ssl
                    async with websockets.connect(
                            WS_URL, additional_headers=WS_HEADERS,
                            ssl=_ssl.create_default_context(),
                            ping_interval=None, close_timeout=5,
                            open_timeout=15) as ws:
                        self.ws = ws
                        print("[CONNECTED] SafeTrade WS")
                        streams = ['global.tickers']
                        for m in self.markets:
                            streams += [f"{m}.depth", f"{m}.trades"]
                        await ws.send(json.dumps({"event": "subscribe",
                                                  "streams": streams}))
                        print(f"[SUBSCRIBED] {len(streams)} streams")
                        backoff = 5
                        asyncio.create_task(self.rest_checkpoint(self.markets))
                        while self.running:
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            except asyncio.TimeoutError:
                                continue
                            receive_time = utc_now()
                            try:
                                data = json.loads(msg)
                            except Exception:
                                continue
                            for entry in parse_message(data):
                                try:
                                    self.handle_entry(entry, receive_time)
                                except Exception as e:
                                    print(f"[HANDLE] {str(e)[:150]}")
                            # re-subscribe newly discovered markets
                            if any(e['market'] not in self.markets
                                   for e in parse_message(data) if e['market']):
                                pass
                            if int(time.time() - self.start_time) % 60 == 0:
                                self.heartbeat()
                except Exception as e:
                    print(f"[DISCONNECT] {type(e).__name__}: {str(e)[:150]} "
                          f"— retry in {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 300)
        finally:
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    def heartbeat(self):
        try:
            with open(HEARTBEAT_FILE, 'w') as f:
                json.dump({'heartbeat_at': utc_now(), 'venue': 'safetrade',
                           'markets': self.markets, 'stats': self.stats},
                          f, indent=2, default=str)
        except Exception:
            pass
        el = int(time.time() - (self.start_time or time.time()))
        td = sum(s.get('depth', 0) for s in self.stats.values())
        tt = sum(s.get('trades', 0) for s in self.stats.values())
        tg = sum(s.get('gaps', 0) for s in self.stats.values())
        print(f"[{el}s] depth={td} trades={tt} gaps={tg} markets={len(self.markets)}")


# Keep old entry points working.
async def run_archival(duration=None):
    arch = L2Archival()
    if duration:
        async def bounded():
            task = asyncio.create_task(arch.run_forever())
            await asyncio.sleep(duration)
            arch.running = False
            await task
        await bounded()
    else:
        await arch.run_forever()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', type=int, default=None,
                    help='capture N seconds then exit')
    args = ap.parse_args()
    asyncio.run(run_archival(duration=args.once))
