"""
Qubic burn + supply snapshot collector.

Polls, no auth required:
  rpc.qubic.org/v1/latest-stats  — circulating supply, burned total,
      price, mcap, epoch/tick, tick quality  (canonical supply figures)
  annexplorer API                 — per-epoch solutions/verification,
      computor leaderboard summaries (never full solution dumps)

Stores one `supply_snapshot` row and one `ann_epoch` row per pass, plus
top-N `ann_computor` rows. Burn *rates* are derived downstream from the
time series (two snapshots = one rate) — never stored as facts.

Usage:
    python3 scripts/burn_snapshot.py --once
"""
import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

ANN = "https://annexplorer.jetskipool.ai"
TOP_COMPUTORS = 25


def _num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def snap_stats(ns_note=None):
    """Poll official stats API. Returns normalized row dict or None."""
    st = fetch_json("https://rpc.qubic.org/v1/latest-stats",
                    source_id="qubic-stats", chain_id="qubic")
    if not st or not isinstance(st, dict):
        return None
    d = st.get("data", st)
    row = {
        "timestamp": d.get("timestamp"),
        "circulating_supply": _num(d.get("circulatingSupply")),
        "burned_total": _num(d.get("burnedQus")),
        "price_usd": d.get("price"),
        "market_cap_usd": _num(d.get("marketCap")),
        "epoch": d.get("epoch"),
        "tick": d.get("currentTick"),
        "tick_quality": d.get("epochTickQuality"),
        "active_addresses": d.get("activeAddresses"),
        "source_role": "canonical",
        "source_id": "qubic-stats",
    }
    if row["circulating_supply"] is None or row["burned_total"] is None:
        return None
    return row


def snap_ann_epochs(limit=10):
    """Latest per-epoch summaries from ANN explorer. Returns list of rows."""
    data = fetch_json(f"{ANN}/api/v1/epochs",
                      source_id="ann-explorer", chain_id="qubic")
    items = (data or {}).get("items", []) if isinstance(data, dict) else []
    rows = []
    for e in items[:limit]:
        v = (e.get("verification") or {})
        rows.append({
            "epoch": e.get("epoch"),
            "algo": e.get("algoFamily"),
            "core_version": e.get("coreVersion"),
            "first_tick": e.get("firstTick"),
            "last_tick": e.get("lastTick"),
            "solutions": e.get("solutions"),
            "verified": v.get("verified"),
            "failed": v.get("failed"),
            "source_role": "derived",
            "source_id": "ann-explorer",
        })
    return rows


def snap_ann_computors(limit=TOP_COMPUTORS):
    """Top computor leaderboard summaries. Returns list of rows."""
    data = fetch_json(f"{ANN}/api/v1/computors",
                      source_id="ann-explorer", chain_id="qubic")
    items = (data or {}).get("items", []) if isinstance(data, dict) else []
    rows = []
    for c in items[:limit]:
        v = (c.get("verification") or {})
        rows.append({
            "computor_id": (c.get("computorId") or "")[:8],
            "rank": c.get("rank"),
            "epochs": c.get("epochsParticipated"),
            "solutions": c.get("solutions"),
            "failed": v.get("failed"),
            "source_role": "derived",
            "source_id": "ann-explorer",
        })
    return rows


def burn_rate_per_day(newer, older):
    """QUBIC/day burned between two supply snapshots.

    Takes dicts with burned_total + timestamp (unix seconds, str or int).
    Returns None when inputs are insufficient or non-monotonic.
    """
    try:
        b1, t1 = int(newer["burned_total"]), int(newer["timestamp"])
        b0, t0 = int(older["burned_total"]), int(older["timestamp"])
    except (KeyError, TypeError, ValueError):
        return None
    dt_days = (t1 - t0) / 86400
    if dt_days <= 0 or b1 < b0:
        return None
    return (b1 - b0) / dt_days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.parse_args()

    s = snap_stats()
    if s:
        store_normalized("supply_snapshot", "qubic", s)
        print(f"[BURN] supply epoch={s['epoch']} "
              f"circ={s['circulating_supply']} burned={s['burned_total']}")
    else:
        print("[BURN] stats API unreachable, skipping supply snapshot")

    epochs = snap_ann_epochs()
    for e in epochs:
        store_normalized("ann_epoch", "qubic", e)
    print(f"[BURN] ann_epoch rows: {len(epochs)}")

    comps = snap_ann_computors()
    for c in comps:
        store_normalized("ann_computor", "qubic", c)
    print(f"[BURN] ann_computor rows: {len(comps)}")


if __name__ == "__main__":
    main()
