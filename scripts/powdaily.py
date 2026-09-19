"""
PowDaily brief — first outlet proof: queries over the garden, not vibes.

Sections: signal board, biggest state changes vs previous STATE date,
new historical extremes (within available history), flow watch
(sell-load leaders), data health. Every claim cites its table + date.
With 1 day of history the change sections degrade honestly.

Usage:
    python3 scripts/powdaily.py --date 2026-09-19
Output:
    briefs/YYYY-MM-DD.md
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

BRIEFS_DIR = os.path.join(BASE_DIR, 'briefs')
os.makedirs(BRIEFS_DIR, exist_ok=True)


def read_table(table):
    rows = []
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', table,
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')

    states = [r for r in read_table('daily_state') if r.get('date')]
    dates = sorted({r['date'] for r in states})
    prev = dates[dates.index(date) - 1] if date in dates and dates.index(date) > 0 else None

    sigs = {}
    for r in read_table('derived_signal'):
        if r.get('date') != date:
            continue
        k = (r.get('asset'), r.get('signal'), r.get('version'))
        if k not in sigs or (r.get('generated_at', '') > sigs[k].get('generated_at', '')):
            sigs[k] = r
    sigs = list(sigs.values())
    cur = [r for r in states if r.get('date') == date]
    old = [r for r in states if r.get('date') == prev] if prev else []

    oldmap = {(r.get('venue'), r.get('symbol')): r for r in old}
    movers = []
    for r in cur:
        o = oldmap.get((r.get('venue'), r.get('symbol')))
        if o and o.get('mid_close') and r.get('mid_close'):
            chg = (r['mid_close'] - o['mid_close']) / o['mid_close']
            movers.append((abs(chg), chg, r))
    movers.sort(key=lambda t: t[0], reverse=True)

    # extremes across all history per symbol-venue
    hist = {}
    for r in states:
        k = (r.get('venue'), r.get('symbol'))
        hist.setdefault(k, []).append(r)

    L = [f"# PowDaily — {date}", ""]
    L.append("## Signal board")
    if sigs:
        for s in sorted(sigs, key=lambda x: x.get('strength', 0), reverse=True):
            L.append(f"- {s['asset']} {s['signal']} ({s.get('version')}): "
                     f"**{s['direction']}** {s.get('strength')} | "
                     f"{'; '.join(s.get('drivers', [])[:3])}")
    else:
        L.append("- no signals this date (thin cross-section or missing emission)")
    L.append("")
    L.append(f"## Biggest moves vs {prev or 'n/a'}")
    if movers:
        for _, chg, r in movers[:8]:
            L.append(f"- {r['venue']}:{r['symbol']} {chg:+.2%} "
                     f"(mid {r.get('mid_close')}, spread {r.get('spread_bps_median')})")
    else:
        L.append("- single-day history: moves activate on day two")
    L.append("")
    L.append("## Flow watch (sell load vs resting book)")
    flows = sorted([r for r in cur if r.get('trade_sell_notional')],
                   key=lambda r: (r['trade_sell_notional'] or 0) /
                   max(r.get('bid_notional_20_mean') or 1, 1), reverse=True)
    for r in flows[:6]:
        load = (r['trade_sell_notional'] or 0) / max(r.get('bid_notional_20_mean') or 1, 1)
        L.append(f"- {r['venue']}:{r['symbol']} sell-load {load:.1f}x "
                 f"(sell ${r['trade_sell_notional']:,.0f} vs book ${r.get('bid_notional_20_mean') or 0:,.0f})")
    if not flows:
        L.append("- no flow data")
    L.append("")
    n_venues = sorted({r.get('venue') for r in cur})
    L.append("## Data health")
    L.append(f"- {len(cur)} market-states across {len(n_venues)} venues "
             f"({', '.join(n_venues) if n_venues else 'none'})")
    L.append(f"- history depth: {len(dates)} STATE dates "
             f"({dates[0]} → {dates[-1]})" if dates else "- no STATE")
    L.append(f"- generated {datetime.now(timezone.utc).isoformat()} from "
             f"warehouse daily_state + derived_signal")
    out = os.path.join(BRIEFS_DIR, f'{date}.md')
    with open(out, 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L[:14]))
    print(f"\n[SAVED] {out}")


if __name__ == '__main__':
    main()
