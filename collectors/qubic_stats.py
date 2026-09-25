"""Qubic official stats — tick quality, active addresses, burns, rich list.

Three unauthenticated endpoints documented in qubic-stats-service and
qubic/integration, verified live 2026-09-25:

    GET  rpc.qubic.org/v1/latest-stats            14 fields incl. active
                                                  addresses, epoch/10k tick
                                                  quality, burned QUs
    GET  rpc.qubic.org/v1/rich-list               paginated top holders
    POST rpc.qubic.org/query/v1/getEventLogs      logType=8 burning events

All three are point-in-time observations of our own, so every row is
classified ephemeral (never dropped for being re-fetchable): the Event Logs
API is explicitly beta and Qubic prunes network data each epoch transition
(Wednesday 12:00 UTC), so if we do not archive it, it is gone.

Usage:
    python3 collectors/qubic_stats.py --once
    python3 collectors/qubic_stats.py --cadence 300
"""

import argparse
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import (
    _archive_raw,
    fetch_json,
    purge_normalized,
    store_normalized,
    utcnow,
)

NETSTATE_FILE = os.path.join(BASE_DIR, "chains", "network_state.json")
PID_FILE = os.path.join(BASE_DIR, "warehouse", "qubic_stats.pid")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "warehouse", "qubic_stats_heartbeat.json")

LATEST_STATS_URL = "https://rpc.qubic.org/v1/latest-stats"
RICH_LIST_URL = "https://rpc.qubic.org/v1/rich-list"
EVENT_LOGS_URL = "https://rpc.qubic.org/query/v1/getEventLogs"

RUNNING = True


def handle_signal(sig, frame):
    global RUNNING
    RUNNING = False


def post_json(url, body, source_id, chain_id, request_params=None):
    """POST with raw archival, mirroring qubic_computors.py."""
    payload = json.dumps(body, default=str).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (PowPowPow)",
        },
    )
    try:
        raw = urllib.request.urlopen(request, timeout=30).read()
        status = 200
    except (urllib.error.URLError, OSError) as exc:
        return None, None, str(exc)[:120]
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None, None, "non-JSON response"
    observation = _archive_raw(
        chain_id=chain_id,
        source_id=source_id,
        endpoint=url,
        event_time=None,
        observed_at=utcnow(),
        response_received=utcnow(),
        http_status=status,
        raw_body=raw.decode("utf-8", "replace"),
        parsed_payload={"keys": list(parsed) if isinstance(parsed, dict) else None},
        request_params=request_params or body,
        quality_flags=["post"],
        transport="http",
        source_role="raw",
    )
    observation_id = (
        observation.get("observation_id")
        if isinstance(observation, dict)
        else observation
    )
    return parsed, observation_id, None


def load_netstate():
    try:
        with open(NETSTATE_FILE) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_netstate(ns):
    tmp = NETSTATE_FILE + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(ns, handle, indent=2, default=str)
    os.replace(tmp, NETSTATE_FILE)


def unwrap(payload):
    """Latest-stats and rich-list are wrapped in {"data": {...}}."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def poll_latest_stats():
    result = fetch_json(
        LATEST_STATS_URL, source_id="qubic-stats", chain_id="qubic", return_result=True
    )
    if not isinstance(result, dict) or not isinstance(result.get("parsed"), dict):
        return None, "latest-stats unreachable"
    data = unwrap(result["parsed"])
    observation_id = result.get("observation_id")

    def as_int(key):
        try:
            return int(data[key])
        except (KeyError, TypeError, ValueError):
            return None

    def as_float(key):
        try:
            return float(data[key])
        except (KeyError, TypeError, ValueError):
            return None

    row = {
        "timestamp": as_int("timestamp"),
        "circulating_supply": as_int("circulatingSupply"),
        "active_addresses": as_int("activeAddresses"),
        "price": as_float("price"),
        "market_cap": as_int("marketCap"),
        "epoch": as_int("epoch"),
        "current_tick": as_int("currentTick"),
        "ticks_in_current_epoch": as_int("ticksInCurrentEpoch"),
        "empty_ticks_in_current_epoch": as_int("emptyTicksInCurrentEpoch"),
        "epoch_tick_quality": as_float("epochTickQuality"),
        "burned_qus": as_int("burnedQus"),
        "ticks_in_last10000": as_int("ticksInLast10000"),
        "empty_ticks_in_last10000": as_int("emptyTicksInLast10000"),
        "last10000_tick_quality": as_float("last10000TickQuality"),
        "source_role": "canonical",
        "source_id": "qubic-stats",
    }
    store_normalized(
        "qubic_stats",
        "qubic",
        row,
        raw_event_id=observation_id,
        event_time=str(row["epoch"] or ""),
    )
    return row, None


def poll_burn_events(epoch, page_size=1000, max_pages=5):
    """Replace this epoch's burn rows so each pass is idempotent.

    `getEventLogs` is beta and caps a single call at size 1000; we page up to
    `max_pages` and keep the newest slice. Older events remain reachable in the
    archived raw responses even after they age out of the normalized page.
    """
    if epoch is None:
        return None, "no epoch"
    epoch_key = str(epoch)
    purge_normalized("qubic_burn_event", "event_time", epoch_key)

    seen = set()
    written = 0
    reported_total = None
    last_error = None
    for offset in range(0, max_pages * page_size, page_size):
        parsed, observation_id, error = post_json(
            EVENT_LOGS_URL,
            {
                "filters": {"logType": "8", "epoch": epoch_key},
                "pagination": {"offset": offset, "size": page_size},
            },
            source_id="qubic-eventlog",
            chain_id="qubic",
        )
        if error:
            last_error = error
            break
        events = (parsed or {}).get("eventLogs") or []
        reported_total = ((parsed or {}).get("hits") or {}).get("total")
        fresh = [e for e in events if e.get("logId") not in seen]
        if not fresh:
            break
        for entry in fresh:
            seen.add(entry.get("logId"))
            burning = entry.get("burning") or {}
            store_normalized(
                "qubic_burn_event",
                "qubic",
                {
                    "epoch": entry.get("epoch"),
                    "tick_number": entry.get("tickNumber"),
                    "timestamp": entry.get("timestamp"),
                    "log_id": entry.get("logId"),
                    "log_digest": entry.get("logDigest"),
                    "categories": entry.get("categories"),
                    "burn_source": burning.get("source"),
                    "burn_amount": burning.get("amount"),
                    "burn_contract_index": burning.get("contractIndex"),
                    "source_role": "canonical",
                    "source_id": "qubic-eventlog",
                },
                raw_event_id=observation_id,
                event_time=epoch_key,
            )
        written += len(fresh)
        if reported_total is not None and offset + page_size >= reported_total:
            break
        if len(events) < page_size:
            break

    if written == 0 and last_error:
        return None, last_error
    return {
        "epoch": epoch,
        "returned": written,
        "total": reported_total,
        "pages": (written // page_size) + 1,
    }, None


def poll_rich_list(page_size=100):
    pages = max(1, (page_size + 99) // 100)
    entities = []
    epoch = None
    observation_id = None
    for page in range(1, pages + 1):
        result = fetch_json(
            f"{RICH_LIST_URL}?page={page}&page_size=100",
            source_id="qubic-richlist",
            chain_id="qubic",
            return_result=True,
        )
        if not isinstance(result, dict) or not isinstance(result.get("parsed"), dict):
            return None, f"rich-list page {page} unreachable"
        payload = unwrap(result["parsed"])
        epoch = epoch or payload.get("epoch")
        observation_id = observation_id or result.get("observation_id")
        entities_container = payload.get("richList") or payload.get("rich_list") or {}
        for entity in entities_container.get("entities") or []:
            entities.append(
                {"identity": entity.get("identity"), "balance": entity.get("balance")}
            )
        if len(entities) >= page_size:
            break
    store_normalized(
        "qubic_rich_list",
        "qubic",
        {
            "epoch": epoch,
            "rank_count": len(entities),
            "entities": entities[:page_size],
            "source_role": "canonical",
            "source_id": "qubic-richlist",
        },
        raw_event_id=observation_id,
        event_time=str(epoch or ""),
    )
    return {"epoch": epoch, "entities": len(entities)}, None


def run_pass(ns, rich_list=False):
    stats = {}
    stats_row, err = poll_latest_stats()
    stats["latest_stats"] = "ok" if stats_row else f"ERR {err}"

    epoch = (stats_row or {}).get("epoch")
    if epoch is None:
        net = ns.get("QUBIC") or {}
        epoch = net.get("epoch")
    burn, err = poll_burn_events(epoch)
    stats["burn_events"] = "ok" if burn else f"ERR {err}"

    if rich_list:
        rich, err = poll_rich_list()
        stats["rich_list"] = "ok" if rich else f"ERR {err}"

    if stats_row:
        entry = ns.setdefault("QUBIC", {})
        entry.update(
            {
                "circulating_supply": stats_row["circulating_supply"],
                "active_addresses": stats_row["active_addresses"],
                "market_cap": stats_row["market_cap"],
                "epoch_tick_quality": stats_row["epoch_tick_quality"],
                "last10000_tick_quality": stats_row["last10000_tick_quality"],
                "burned_qus": stats_row["burned_qus"],
                "burned_qus_source": "rpc.qubic.org/v1/latest-stats",
                "stats_source": "rpc.qubic.org/v1/latest-stats",
                "stats_as_of": utcnow(),
                "as_of": utcnow(),
            }
        )
        if stats_row.get("price") and stats_row.get("market_cap"):
            entry["price_usd"] = stats_row["price"]
        save_netstate(ns)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--cadence", type=int, default=300)
    ap.add_argument(
        "--rich-list-every",
        type=int,
        default=12,
        help="passes between rich-list snapshots",
    )
    args = ap.parse_args()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    if args.once:
        print(run_pass(load_netstate(), rich_list=True))
        return

    with open(PID_FILE, "w") as handle:
        handle.write(str(os.getpid()))
    print(f"[QUBIC_STATS] cadence={args.cadence}s pid={os.getpid()}")
    pass_no = 0
    try:
        while RUNNING:
            pass_no += 1
            try:
                stats = run_pass(
                    load_netstate(), rich_list=(pass_no % args.rich_list_every == 1)
                )
            except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
                stats = {"error": f"{type(exc).__name__}: {exc}"[:140]}
            try:
                with open(HEARTBEAT_FILE, "w") as handle:
                    json.dump(
                        {
                            "heartbeat_at": utcnow(),
                            "mode": "daemon",
                            "pass": pass_no,
                            "stats": stats,
                        },
                        handle,
                        indent=2,
                        default=str,
                    )
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
