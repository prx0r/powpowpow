"""QUBIC transfer activity — measured address activity and exchange netflow.

The official `activeAddresses` counter in `/v1/latest-stats` is a coarse
snapshot: it did not move at all across sixteen minutes of five-minute
snapshots. `getEventLogs` with `logType=0` returns individual `quTransfer`
records carrying source, destination and amount, so activity can be measured
over a real window instead of trusted as a stale counter.

    POST rpc.qubic.org/query/v1/getEventLogs
        {"filters":{"epoch":"232","logType":"0"},"pagination":{"offset":0,"size":1000}}

Response is newest-first and capped at 10,000 total, so each pass stores a
rolling window of the most recent transfers plus aggregates.

Usage:
    python3 collectors/qubic_transfers.py --once
    python3 collectors/qubic_transfers.py --cadence 300
"""

import argparse
import json
import os
import signal
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from collectors.qubic_stats import post_json as post_json_like
from core import store_normalized, utcnow

EVENT_LOGS_URL = "https://rpc.qubic.org/query/v1/getEventLogs"
REGISTRY_FILE = os.path.join(BASE_DIR, "warehouse", "knowledge",
                             "qubic_exchanges.json")
PID_FILE = os.path.join(BASE_DIR, "warehouse", "qubic_transfers.pid")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "warehouse",
                              "qubic_transfers_heartbeat.json")

WHALE_THRESHOLD = 1_000_000_000
PAGE_SIZE = 1000

RUNNING = True


def handle_signal(sig, frame):
    global RUNNING
    RUNNING = False


def load_exchange_identities():
    try:
        with open(REGISTRY_FILE) as handle:
            entries = json.load(handle).get("exchanges") or []
    except (OSError, ValueError):
        return set()
    return {str(e.get("address")).upper() for e in entries if e.get("address")}


def fetch_transfers(epoch):
    parsed, observation_id, error = post_json_like(
        EVENT_LOGS_URL,
        {"filters": {"epoch": str(epoch), "logType": "0"},
         "pagination": {"offset": 0, "size": PAGE_SIZE}},
        source_id="qubic-eventlog", chain_id="qubic")
    if error:
        return None, None, error
    events = (parsed or {}).get("eventLogs") or []
    total = ((parsed or {}).get("hits") or {}).get("total")
    return events, observation_id, total


def aggregate(events, exchanges):
    """Fold a transfer window into one row. Pure, testable."""
    if not events:
        return None
    transfers = []
    for event in events:
        payload = event.get("quTransfer") or {}
        amount = payload.get("amount")
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            continue
        transfers.append({
            "tick": event.get("tickNumber"),
            "timestamp": event.get("timestamp"),
            "source": str(payload.get("source") or "").upper(),
            "destination": str(payload.get("destination") or "").upper(),
            "amount": amount,
        })
    if not transfers:
        return None

    addresses = set()
    inflow = outflow = whale_volume = 0
    whale_count = 0
    for row in transfers:
        if row["source"]:
            addresses.add(row["source"])
        if row["destination"]:
            addresses.add(row["destination"])
        if row["source"] in exchanges:
            inflow += row["amount"]
        if row["destination"] in exchanges:
            outflow += row["amount"]
        if row["amount"] >= WHALE_THRESHOLD:
            whale_count += 1
            whale_volume += row["amount"]

    ticks = sorted(t["tick"] for t in transfers if t["tick"] is not None)
    stamps = sorted(int(t["timestamp"]) for t in transfers if t["timestamp"])
    span_seconds = None
    if len(stamps) > 1:
        span_seconds = (stamps[-1] - stamps[0]) / 1000

    return {
        "epoch": transfers[0].get("epoch") or None,
        "tick_from": ticks[0] if ticks else None,
        "tick_to": ticks[-1] if ticks else None,
        "window_seconds": round(span_seconds, 3) if span_seconds else None,
        "n_transfers": len(transfers),
        "unique_addresses": len(addresses),
        "total_volume": sum(t["amount"] for t in transfers),
        "max_amount": max(t["amount"] for t in transfers),
        "exchange_inflow": inflow,
        "exchange_outflow": outflow,
        "exchange_netflow": outflow - inflow,
        "whale_count": whale_count,
        "whale_volume": whale_volume,
        "whale_share_of_volume": (round(whale_volume / sum(t["amount"]
                                                          for t in transfers), 4)
                                  if sum(t["amount"] for t in transfers) else None),
        "source_role": "canonical",
        "source_id": "qubic-eventlog",
    }


def run_pass():
    stats = {}
    try:
        import urllib.request
        tick_request = urllib.request.Request(
            "https://rpc.qubic.org/v1/tick-info",
            headers={"User-Agent": "Mozilla/5.0 (PowPowPow)"})
        tick_info = json.loads(urllib.request.urlopen(
            tick_request, timeout=20).read())
        epoch = (tick_info.get("tickInfo") or {}).get("epoch")
    except (OSError, ValueError) as exc:
        return {"transfers": f"ERR {type(exc).__name__}"[:60]}
    if not epoch:
        return {"transfers": "ERR no epoch"}

    events, observation_id, total = fetch_transfers(epoch)
    if events is None:
        return {"transfers": "ERR fetch failed"}
    exchanges = load_exchange_identities()
    row = aggregate(events, exchanges)
    if not row:
        return {"transfers": "ERR no transfer events", "epoch": epoch}
    row["epoch"] = epoch
    store_normalized("qubic_transfer_window", "qubic", row,
                     raw_event_id=observation_id,
                     event_time=str(epoch))
    stats.update({
        "transfers": "ok",
        "epoch": epoch,
        "n": row["n_transfers"],
        "unique_addresses": row["unique_addresses"],
        "exchange_netflow": row["exchange_netflow"],
        "available_total": total,
    })
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--cadence", type=int, default=300)
    args = ap.parse_args()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    if args.once:
        print(run_pass())
        return

    with open(PID_FILE, "w") as handle:
        handle.write(str(os.getpid()))
    print(f"[QUBIC_TRANSFERS] cadence={args.cadence}s pid={os.getpid()}")
    pass_no = 0
    try:
        while RUNNING:
            pass_no += 1
            try:
                stats = run_pass()
            except (OSError, ValueError, TypeError, KeyError,
                    RuntimeError) as exc:
                stats = {"error": f"{type(exc).__name__}: {exc}"[:140]}
            try:
                with open(HEARTBEAT_FILE, "w") as handle:
                    json.dump({"heartbeat_at": utcnow(), "mode": "daemon",
                               "pass": pass_no, "stats": stats}, handle,
                              indent=2, default=str)
            except OSError:
                pass
            print(f"[PASS {pass_no}] {stats}", flush=True)
            for _ in range(args.cadence):
                if not RUNNING:
                    break
                time.sleep(1)
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
