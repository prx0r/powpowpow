"""
epoch_burn — derived job: measured burn aggregated per epoch/day/contract.

Reads warehouse/normalized/burn_event rows (see collectors/burn_ledger.py),
excludes genesis placeholders (pre-mainnet timestamps), and writes
warehouse/epoch_burn.json consumed by /api/burns.

Also emits the honesty panel: measured tx-burn/day vs the viral 225B/day
claim (which is SupplyWatcher revenue donation, NOT BURNING events).

Usage: python3 scripts/epoch_burn.py
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402

OUT = os.path.join(BASE_DIR, "warehouse", "epoch_burn.json")
REGISTRY = os.path.join(BASE_DIR, "warehouse", "qubic_contracts.json")
GENESIS_CUTOFF_MS = 1704067200000  # 2024-01-01: anything older is placeholder
DAY_MS = 86_400_000


def load_events():
    rows = []
    for f in glob.glob(os.path.join(BASE_DIR, "warehouse", "normalized",
                                    "burn_event", "**", "*.jsonl"),
                       recursive=True):
        for line in open(f):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def load_registry():
    try:
        return {str(c["index"]): c["name"]
                for c in json.load(open(REGISTRY))}
    except (OSError, ValueError, KeyError):
        return {}


def aggregate(rows):
    names = load_registry()
    genesis, live = [], []
    for r in rows:
        try:
            ts = int(r.get("event_time_ms", 0))
            amt = int(r.get("amount", 0))
        except (TypeError, ValueError):
            continue
        (genesis if ts < GENESIS_CUTOFF_MS else live).append((ts, amt, r))
    by_epoch = defaultdict(int)
    by_contract = Counter()
    for ts, amt, r in live:
        by_epoch[r.get("epoch")] += amt
        by_contract[str(r.get("contract"))] += amt
    total = sum(a for _, a, _ in live)
    per_day = None
    if live:
        span_days = (max(t for t, _, _ in live)
                     - min(t for t, _, _ in live)) / DAY_MS
        if span_days >= 1:
            per_day = total / span_days
    return {
        "as_of": utcnow(),
        "events_live": len(live),
        "events_genesis_excluded": len(genesis),
        "genesis_total": sum(a for _, a, _ in genesis),
        "burn_total_live": total,
        "burn_per_day_measured": per_day,
        "by_epoch": {str(k): v for k, v in sorted(by_epoch.items())},
        "by_contract": {names.get(k, f"contract-{k}"): v
                        for k, v in by_contract.most_common()},
        "note": ("BURNING-event burns only (contract fees etc). "
                 "SupplyWatcher revenue donations move as transfers, "
                 "not burn events — tracked separately."),
    }


def main():
    out = aggregate(load_events())
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, OUT)
    print(f"[EPOCH_BURN] live={out['events_live']} "
          f"total={out['burn_total_live']} "
          f"per_day={out['burn_per_day_measured']}")


if __name__ == "__main__":
    main()
