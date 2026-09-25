"""
Depth snapshot collector — representative top-of-book for chains whose real
market is not SafeTrade.

SafeTrade's BTC/XMR books are ~$168 / ~$29 deep on 89 / 37 trades a day, so
`burden_vs_book` computed there measures SafeTrade rather than the market
(see signals.SECONDARY_DEPTH_VENUES, which refuses exactly that). This polls
REST depth *snapshots* — not tick streams — from venues where those chains
actually trade, at 300s cadence: enough for a resting top-20 denominator,
cheap enough to run beside the SafeTrade L2 archiver.

Sources (public, no auth):
    Coinbase  GET https://api.exchange.coinbase.com/products/{pair}/book?level=2
    Kraken    GET https://api.kraken.com/0/public/Depth?pair={pair}&count=25

Rows land in `orderbook_snapshot` under chain=venue, which build_daily_state,
factors and signals already read — no plumbing change. Raw responses are
archived before parsing (moat rule: ephemeral depth vanishes).

Usage:
    python3 collectors/depth_snapshots.py --once     # single pass (test/cron)
    python3 collectors/depth_snapshots.py            # daemon loop (supervised)
"""

import argparse
import json
import os
import shutil
import signal
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

# (venue, chain, request payload, canonical pair symbol)
SOURCES = [
    ("coinbase", "BTC", {"pair": "BTC-USD", "symbol": "btcusd"}, "coinbase-depth"),
    ("kraken", "XMR", {"pair": "XMRUSD", "symbol": "xmrusd"}, "kraken-depth"),
    ("kraken", "BTC", {"pair": "XBTUSD", "symbol": "btcusd"}, "kraken-depth"),
]

HEARTBEAT_FILE = os.path.join(BASE_DIR, "warehouse", "depth_snapshots_heartbeat.json")
MIN_FREE_BYTES = int(os.environ.get("POW_MIN_FREE_BYTES", 2 * 1024**3))
CADENCE = int(os.environ.get("POW_DEPTH_CADENCE", 300))

RUNNING = True


def handle_signal(sig, frame):
    global RUNNING
    RUNNING = False


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metrics(bids, asks):
    """mid, spread_bps, top-20 bid/ask notional — all in quote currency (USD)."""
    try:
        bb = _f(bids[0][0]) if bids else None
        ba = _f(asks[0][0]) if asks else None
        mid = (bb + ba) / 2 if bb is not None and ba is not None else None
        spread = (ba - bb) / mid * 10000 if mid else None
        bid_n = sum(_f(p) * _f(q) for p, q in bids[:20])
        ask_n = sum(_f(p) * _f(q) for p, q in asks[:20])
        return mid, spread, bid_n, ask_n
    except (TypeError, ValueError, IndexError):
        return None, None, None, None


def parse_coinbase(payload):
    if not isinstance(payload, dict):
        return None
    bids = [[r[0], r[1]] for r in payload.get("bids") or [] if len(r) >= 2]
    asks = [[r[0], r[1]] for r in payload.get("asks") or [] if len(r) >= 2]
    return bids, asks, None


def parse_kraken(payload):
    if not isinstance(payload, dict) or payload.get("error"):
        return None
    result = payload.get("result") or {}
    if not result:
        return None
    book = next(iter(result.values()))
    if not isinstance(book, dict):
        return None
    bids = [[r[0], r[1]] for r in book.get("bids") or [] if len(r) >= 2]
    asks = [[r[0], r[1]] for r in book.get("asks") or [] if len(r) >= 2]
    return bids, asks, None


def request(venue, spec):
    if venue == "coinbase":
        return (
            f"https://api.exchange.coinbase.com/products/{spec['pair']}/book?level=2",
            {"level": "2"},
        )
    if venue == "kraken":
        return "https://api.kraken.com/0/public/Depth", {
            "pair": spec["pair"],
            "count": 25,
        }
    raise ValueError(f"unknown venue {venue}")


def poll(venue, spec, source_id, receive_time):
    """Fetch one book, archive raw, write a normalized snapshot. Returns stats."""
    url, params = request(venue, spec)
    result = (
        fetch_json(
            url,
            params=params,
            source_id=source_id,
            chain_id="venue",
            event_type="depth_snapshot",
            return_result=True,
        )
        or {}
    )
    parsed = result.get("parsed")
    obs_id = result.get("observation_id")
    parser = parse_coinbase if venue == "coinbase" else parse_kraken
    book = parser(parsed)
    if book is None:
        return {"ok": False, "reason": "unparseable_payload"}
    bids, asks, _ = book
    if not bids and not asks:
        return {"ok": False, "reason": "empty_book"}
    mid, spread, bid_n, ask_n = metrics(bids, asks)
    row = {
        "venue": venue,
        "symbol": spec["symbol"],
        "market": spec["pair"],
        "receive_time": receive_time,
        "mid": mid,
        "spread_bps": spread,
        "bid_notional_20": bid_n,
        "ask_notional_20": ask_n,
        "bids": bids[:20],
        "asks": asks[:20],
        "snapshot_kind": "rest_poll",
        "source_role": "raw_venue",
        "raw_event_id": obs_id,
    }
    store_normalized("orderbook_snapshot", "venue", row, raw_event_id=obs_id)
    return {"ok": True, "mid": mid, "bid": bid_n, "levels": max(len(bids), len(asks))}


def write_heartbeat(stats):
    try:
        os.makedirs(os.path.dirname(HEARTBEAT_FILE), exist_ok=True)
        with open(HEARTBEAT_FILE, "w") as handle:
            json.dump(
                {"heartbeat_at": utcnow(), **stats}, handle, indent=2, default=str
            )
    except OSError:
        pass


def disk_low():
    try:
        return shutil.disk_usage(BASE_DIR).free < MIN_FREE_BYTES
    except OSError:
        return False


def cycle(state):
    receive_time = utcnow()
    results = []
    for venue, chain, spec, source_id in SOURCES:
        try:
            outcome = poll(venue, spec, source_id, receive_time)
        except Exception as exc:  # network/parse errors must not kill the loop
            outcome = {"ok": False, "reason": f"{type(exc).__name__}: {exc}"[:160]}
        key = f"{venue}:{spec['symbol']}"
        state["last"][key] = {"at": receive_time, **outcome}
        state["polls"] += 1
        if outcome.get("ok"):
            state["ok"] += 1
        else:
            state["failed"] += 1
            print(f"[DEPTH] {key} {outcome.get('reason')}", flush=True)
        results.append(outcome)
        time.sleep(1)  # be polite to public endpoints
    write_heartbeat(state)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single pass then exit")
    ap.add_argument("--cadence", type=int, default=CADENCE)
    args = ap.parse_args()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    state = {"polls": 0, "ok": 0, "failed": 0, "last": {}, "cadence": args.cadence}
    print(f"[DEPTH] sources={len(SOURCES)} cadence={args.cadence}s", flush=True)
    while RUNNING:
        if disk_low():
            state["disk_low"] = True
            print(f"[DISK] waiting for {MIN_FREE_BYTES} free bytes", flush=True)
            write_heartbeat(state)
            time.sleep(300)
            continue
        state.pop("disk_low", None)
        cycle(state)
        if args.once:
            break
        deadline = time.time() + args.cadence
        while RUNNING and time.time() < deadline:
            time.sleep(1)
    write_heartbeat(state)
    print(
        f"[DEPTH] stopped after {state['polls']} polls "
        f"({state['ok']} ok / {state['failed']} failed)",
        flush=True,
    )


if __name__ == "__main__":
    main()
