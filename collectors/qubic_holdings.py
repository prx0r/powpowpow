"""QUBIC holdings — exchange reserves and wealth concentration.

Answers two questions the network does not answer for itself:

  * how much circulating supply sits on labelled exchange wallets
  * how concentrated the remaining wealth is

Endpoints, all verified live 2026-09-25:

    GET https://static.qubic.org/v1/general/data/exchanges.json
        name -> identity, 18 entries (qubic/static repo)
    GET https://rpc.qubic.org/live/v1/balances/{identity}
        current balance + validForTick
    GET https://rpc.qubic.org/v1/rich-list?page=&page_size=100
        top holders, capped at 10,000 records (100 pages)

Usage:
    python3 collectors/qubic_holdings.py --once
    python3 collectors/qubic_holdings.py --cadence 300 --concentration-every 72
"""

import argparse
import json
import os
import signal
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow
from transforms.holdings import (
    exchange_reserve,
    exchange_share_of_top_holders,
    wealth_concentration,
)

EXCHANGES_URL = "https://static.qubic.org/v1/general/data/exchanges.json"
BALANCE_URL = "https://rpc.qubic.org/live/v1/balances/{}"
RICH_LIST_URL = "https://rpc.qubic.org/v1/rich-list?page={}&page_size=100"
RICH_LIST_PAGES = 100

REGISTRY_FILE = os.path.join(BASE_DIR, "warehouse", "knowledge",
                             "qubic_exchanges.json")
PID_FILE = os.path.join(BASE_DIR, "warehouse", "qubic_holdings.pid")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "warehouse", "qubic_holdings_heartbeat.json")

RUNNING = True


def handle_signal(sig, frame):
    global RUNNING
    RUNNING = False


def load_registry():
    """Exchange labels from static.qubic.org, falling back to last cache."""
    result = fetch_json(EXCHANGES_URL, source_id="qubic-static",
                        chain_id="qubic", return_result=True)
    exchanges = None
    if isinstance(result, dict) and isinstance(result.get("parsed"), dict):
        exchanges = result["parsed"].get("exchanges")
    if isinstance(exchanges, list) and exchanges:
        try:
            os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
            tmp = REGISTRY_FILE + ".tmp"
            with open(tmp, "w") as handle:
                json.dump({"fetched_at": utcnow(), "source": EXCHANGES_URL,
                           "exchanges": exchanges}, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, REGISTRY_FILE)
        except OSError:
            pass
        return exchanges, None
    try:
        with open(REGISTRY_FILE) as handle:
            cached = json.load(handle).get("exchanges") or []
    except (OSError, ValueError):
        cached = []
    if cached:
        return cached, "registry served from local cache"
    return [], "exchange registry unavailable"


def poll_exchange_balances(exchanges):
    if not exchanges:
        return None, "no exchange registry"
    written = 0
    total = 0
    snapshot = []
    for entry in exchanges:
        identity = entry.get("address")
        if not identity:
            continue
        result = fetch_json(BALANCE_URL.format(identity),
                            source_id="qubic-balance", chain_id="qubic",
                            return_result=True)
        payload = result.get("parsed") if isinstance(result, dict) else None
        if isinstance(payload, dict) and isinstance(payload.get("balance"), dict):
            payload = payload["balance"]
        balance = None
        if isinstance(payload, dict):
            try:
                balance = int(payload.get("balance"))
            except (TypeError, ValueError):
                balance = None
        if balance is None:
            continue
        observation_id = result.get("observation_id")
        snapshot.append({"name": entry.get("name"), "address": identity,
                         "balance": balance})
        store_normalized(
            "qubic_exchange_balance", "qubic",
            {
                "name": entry.get("name"),
                "address": identity,
                "balance": balance,
                "valid_for_tick": payload.get("validForTick"),
                "source_role": "canonical",
                "source_id": "qubic-static+live/balances",
            },
            raw_event_id=observation_id,
            event_time=str(payload.get("validForTick") or ""))
        written += 1
        total += balance
    if written == 0:
        return None, "no exchange balances returned"
    _exchange_snapshot.clear()
    _exchange_snapshot.extend(snapshot)
    return {"entities": written, "total": total}, None


def poll_wealth_concentration():
    entities = []
    epoch = None
    last_error = None
    for page in range(1, RICH_LIST_PAGES + 1):
        result = fetch_json(RICH_LIST_URL.format(page),
                            source_id="qubic-richlist", chain_id="qubic",
                            return_result=True)
        if not isinstance(result, dict) or not isinstance(result.get("parsed"), dict):
            last_error = f"rich-list page {page} unreachable"
            break
        payload = result["parsed"]
        epoch = epoch or payload.get("epoch")
        rows = (payload.get("richList") or {}).get("entities") or []
        if not rows:
            break
        entities.extend(rows)
    if not entities:
        return None, last_error or "rich list empty"

    concentration = wealth_concentration([row.get("balance") for row in entities])
    exchange_share = exchange_share_of_top_holders(
        [entry.get("address") for entry in _cached_exchanges], entities)
    if concentration.get("refused"):
        return None, concentration.get("reason")

    store_normalized(
        "qubic_wealth_concentration", "qubic",
        {
            "epoch": epoch,
            "gini": concentration["value"],
            "holders": concentration["n"],
            "total_held": concentration.get("total_held"),
            "mean_balance": concentration.get("mean_balance"),
            "median_balance": concentration.get("median_balance"),
            "mean_to_median": concentration.get("mean_to_median"),
            "shares": concentration.get("shares"),
            "exchange_share_of_top_holders": exchange_share.get("value"),
            "exchange_labelled_in_top": exchange_share.get("labelled_in_top"),
            "source_role": "canonical",
            "source_id": "qubic-richlist+qubic-static",
        },
        event_time=str(epoch or ""))
    return {"epoch": epoch, "holders": concentration["n"],
            "gini": concentration["value"]}, None


_cached_exchanges = []


def run_pass(concentration=False):
    global _cached_exchanges
    stats = {}
    exchanges, err = load_registry()
    if exchanges:
        _cached_exchanges = exchanges
    stats["exchange_registry"] = ("ok" if exchanges
                                  else f"ERR {err}")

    supply = _latest_circulating_supply()
    balances, err = poll_exchange_balances(_cached_exchanges)
    stats["exchange_balances"] = "ok" if balances else f"ERR {err}"
    if balances and _exchange_snapshot:
        reserve = exchange_reserve(_exchange_snapshot,
                                   circulating_supply=supply,
                                   expected_entities=len(_cached_exchanges))
        stats["exchange_reserve_qu"] = reserve.get("value")
        stats["exchange_reserve_partial"] = reserve.get("partial")
        stats["exchange_share_of_supply_pct"] = reserve.get(
            "share_of_supply_pct")

    if concentration:
        wealth, err = poll_wealth_concentration()
        stats["wealth_concentration"] = "ok" if wealth else f"ERR {err}"
        if wealth:
            stats["gini"] = wealth.get("gini")
    return stats


_exchange_snapshot = []


def _latest_circulating_supply():
    rows = []
    pattern = os.path.join(BASE_DIR, "warehouse", "normalized", "qubic_stats",
                           "chain=qubic", "date=*", "hour=*.jsonl")
    import glob
    for path in glob.glob(pattern):
        try:
            with open(path) as handle:
                for line in handle:
                    if line.strip():
                        rows.append(json.loads(line))
        except (OSError, ValueError):
            continue
    if not rows:
        return None
    rows.sort(key=lambda row: row.get("observed_at") or "")
    value = rows[-1].get("circulating_supply")
    return int(value) if value else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--cadence", type=int, default=300)
    ap.add_argument("--concentration-every", type=int, default=72,
                    help="passes between full rich-list scans")
    args = ap.parse_args()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    if args.once:
        print(run_pass(concentration=True))
        return

    with open(PID_FILE, "w") as handle:
        handle.write(str(os.getpid()))
    print(f"[QUBIC_HOLDINGS] cadence={args.cadence}s pid={os.getpid()}")
    pass_no = 0
    try:
        while RUNNING:
            pass_no += 1
            try:
                stats = run_pass(
                    concentration=(pass_no % args.concentration_every == 1))
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
