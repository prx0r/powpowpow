"""
Daily brief — interesting-things pipeline, no X required.

Reads warehouse history (factors, orderbook, supply, burn, epoch) and emits
warehouse/daily_brief.json: per-coin tape deltas, chain highlights, anomaly
flags with hook-picker scores (surprise x receipts x face).

Usage: python3 scripts/daily_brief.py
"""
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402

OUT = os.path.join(BASE_DIR, "warehouse", "daily_brief.json")
COINS = ("QUBIC", "XMR", "PRL")
DAY = 24 * 3600


def read_table(table, chain):
    rows = []
    for f in glob.glob(os.path.join(
            BASE_DIR, "warehouse", "normalized", table,
            f"chain={chain}", "date=*", "hour=*.jsonl")):
        for line in open(f):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def ts_of(r):
    for k in ("observed_at", "as_of", "timestamp", "computed_at"):
        v = r.get(k)
        if v:
            try:
                return datetime.fromisoformat(str(v).replace("Z", "+00:00")
                                              ).timestamp()
            except ValueError:
                continue
    return 0


def latest_before(rows, cutoff):
    cands = [r for r in rows if ts_of(r) <= cutoff]
    return max(cands, key=ts_of) if cands else None


def num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def flag(text, surprise, receipts, face, feed):
    return {"text": text, "feed": feed,
            "score": {"surprise": surprise, "receipts": receipts,
                      "face": face, "total": surprise * receipts * face}}


def brief_qubic(now, factors):
    flags = []
    sup = read_table("supply_snapshot", "qubic")
    new, old = latest_before(sup, now), latest_before(sup, now - DAY)
    if new and old:
        b1, b0 = num(new.get("burned_total")), num(old.get("burned_total"))
        t1, t0 = ts_of(new), ts_of(old)
        if b1 is not None and b0 is not None and t1 > t0 and b1 >= b0:
            rate = (b1 - b0) / ((t1 - t0) / DAY)
            flags.append(flag(f"protocol burn pace {rate / 1e9:.1f}B QU/day",
                              2 if rate > 100e9 else 1, 3, 2, "CHAIN"))
    try:
        eb = json.load(open(os.path.join(BASE_DIR, "warehouse",
                                         "epoch_burn.json")))
        per_day = eb.get("burn_per_day_measured")
        if per_day:
            flags.append(flag(f"measured fee burns "
                              f"{per_day / 1e9:.2f}B QU/day "
                              f"(QEARN-led)", 2, 3, 2, "CHAIN"))
    except (OSError, ValueError):
        pass
    ep = read_table("ann_epoch", "qubic")
    ep = [r for r in ep if ts_of(r) <= now and r.get("epoch") is not None]
    e = max(ep, key=lambda r: (r["epoch"], ts_of(r))) if ep else None
    if e and e.get("epoch"):
        flags.append(flag(f"epoch {e['epoch']} live, "
                          f"{e.get('solutions', '?')} solutions scored",
                          1, 3, 1, "CHAIN"))
    return flags


def brief_tape(sym, now, factors):
    flags = []
    f = (factors.get(sym) or {})
    buy, sell = num(f.get("trade_buy_notional")), num(f.get("trade_sell_notional"))
    if buy and sell:
        r = buy / sell if sell else 0
        if r >= 1.5:
            flags.append(flag(f"buyers {r:.1f}x sellers, "
                              f"${buy + sell:,.0f} volume", 2, 3, 2, "TAPE"))
        elif r <= 0.67:
            flags.append(flag(f"sellers {1 / r:.1f}x buyers, "
                              f"${buy + sell:,.0f} volume", 2, 3, 2, "TAPE"))
    b = num(f.get("burden_vs_book"))
    if b is not None and b >= 5:
        flags.append(flag(f"burden {b:.1f}x: emission dwarfs the book",
                          2, 3, 2, "TAPE"))
    s = num(f.get("spread_bps_median"))
    if s is not None and s >= 80:
        flags.append(flag(f"spread {s:.0f} bps, liquidity thin", 1, 3, 1, "TAPE"))
    return flags


def main():
    now = datetime.now(timezone.utc).timestamp()
    try:
        factors = json.load(open(os.path.join(
            BASE_DIR, "chains", "factors", "cross_chain_factors.json")))
    except (OSError, ValueError):
        factors = {}
    brief = {"as_of": utcnow(), "coins": {}}
    for sym in COINS:
        flags = brief_tape(sym, now, factors)
        if sym == "QUBIC":
            flags += brief_qubic(now, factors)
        flags.sort(key=lambda x: -x["score"]["total"])
        f = factors.get(sym) or {}
        brief["coins"][sym] = {
            "price_usd": f.get("price_usd"),
            "volume_24h": f.get("trade_notional_24h"),
            "bids_20": f.get("bid_notional_20_sum"),
            "burden": f.get("burden_vs_book"),
            "hook": flags[0] if flags else None,
            "flags": flags,
        }
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(brief, fh, indent=2)
    os.replace(tmp, OUT)
    for sym, b in brief["coins"].items():
        h = b["hook"]
        print(f"[{sym}] hook={h['text'] if h else 'quiet day'} "
              f"(x{h['score']['total'] if h else 0})")


if __name__ == "__main__":
    main()
