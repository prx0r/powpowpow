"""
Qubic burn ledger collector — measured on-chain burns.

Queries rpc.qubic.org Query API event logs for BURNING events
(logType 8; logType 9 dust included when present) and stores one
`burn_event` row per event. Incremental: a cursor file holds the highest
logId seen, each pass walks forward until it meets stored data.

This is MEASURED burn (contract fees, null-address sends that surface as
events). Protocol schedule burn (77.5% max) is separate — see epoch engine.

Usage:
    python3 collectors/burn_ledger.py --once
    python3 collectors/burn_ledger.py --pages 5 --size 500
"""
import argparse
import json
import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import store_normalized, utcnow  # noqa: E402

RPC = "https://rpc.qubic.org/query/v1/getEventLogs"
CURSOR_FILE = os.path.join(BASE_DIR, "warehouse", "burn_ledger_cursor.json")
PAGE_SIZE = 500
MAX_PAGES = 5


def post(payload, timeout=30):
    req = urllib.request.Request(
        RPC, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "PowPowPow/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_page(log_type, offset, size=PAGE_SIZE):
    d = post({"filters": {"logType": str(log_type)},
              "pagination": {"offset": offset, "size": size}})
    return (d.get("eventLogs") or []), (d.get("hits") or {}).get("total")


def parse_event(e):
    """Normalize one event-log entry. Returns None when unusable."""
    b = e.get("burning") or {}
    try:
        amount = int(b.get("amount", "0"))
    except (TypeError, ValueError):
        return None
    try:
        log_id = int(e.get("logId", "-1"))
    except (TypeError, ValueError):
        return None
    try:
        ts_ms = int(e.get("timestamp", "0"))
    except (TypeError, ValueError):
        return None
    if amount <= 0 or log_id < 0 or ts_ms <= 0:
        return None
    return {
        "log_id": log_id,
        "tick": e.get("tickNumber"),
        "epoch": e.get("epoch"),
        "event_time_ms": ts_ms,
        "log_type": e.get("logType"),
        "source": b.get("source"),
        "amount": amount,
        "contract": b.get("contractIndex"),
        "categories": e.get("categories") or [],
        "tx": e.get("transactionHash"),
        "source_role": "canonical",
        "source_id": "qubic-query-events",
    }


def load_cursor():
    try:
        return int(json.load(open(CURSOR_FILE)).get("last_log_id", -1))
    except (OSError, ValueError, TypeError, AttributeError):
        return -1


def save_cursor(last_log_id):
    tmp = CURSOR_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"last_log_id": last_log_id, "as_of": utcnow()}, f)
    os.replace(tmp, CURSOR_FILE)


def run_pass(max_pages=MAX_PAGES, size=PAGE_SIZE):
    """Walk newest-first per log type until stored cursor. Returns stats."""
    cursor = load_cursor()
    stats = {"new": 0, "skipped": 0, "top_log_id": cursor}
    for log_type in (8, 9):
        offset = 0
        for _ in range(max_pages):
            events, _ = fetch_page(log_type, offset, size)
            if not events:
                break
            done = False
            for e in events:
                row = parse_event(e)
                if row is None:
                    continue
                if row["log_id"] <= cursor:
                    done = True
                    stats["skipped"] += 1
                    continue
                store_normalized("burn_event", "qubic", row)
                stats["new"] += 1
                stats["top_log_id"] = max(stats["top_log_id"], row["log_id"])
            offset += size
            if done or len(events) < size:
                break
    if stats["top_log_id"] > cursor:
        save_cursor(stats["top_log_id"])
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--pages", type=int, default=MAX_PAGES)
    ap.add_argument("--size", type=int, default=PAGE_SIZE)
    args = ap.parse_args()
    stats = run_pass(max_pages=args.pages, size=args.size)
    print(f"[BURN_LEDGER] new={stats['new']} skipped={stats['skipped']} "
          f"cursor={stats['top_log_id']}")


if __name__ == "__main__":
    main()
