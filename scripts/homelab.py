"""
Homelab recommend — detect this machine, join to POW opportunity set.

Read-only: prints what the machine should do and saves the report
(predicted side of the future expected-vs-realized join). No execution,
no grants, no wallet access.

Usage:
    python3 scripts/homelab.py
    python3 scripts/homelab.py --electricity 0.09 --out warehouse/homelab/report.json
    python3 scripts/homelab.py --inventory-only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from homelab import inventory, recommend  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--electricity', type=float, default=0.10)
    ap.add_argument('--date', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--inventory-only', action='store_true')
    args = ap.parse_args()

    inv = inventory(electricity=args.electricity)
    cpu = inv.get('cpu', {})
    print(f"[INVENTORY {inv['fingerprint']}] {cpu.get('model') or 'unknown CPU'}"
          f" x{cpu.get('threads') or '?'} | RAM {inv.get('memory', {}).get('total_gb') or '?'}GB"
          f" | GPUs {[g.get('name') for g in inv.get('gpus', [])] or 'none'}"
          f" | elec ${args.electricity}/kWh")

    if args.inventory_only:
        print(json.dumps(inv, indent=2, default=str))
        return

    rep = recommend(inv, date=args.date, electricity=args.electricity)
    print(f"[COVERAGE] {rep['opportunity_coverage']}")
    for r in rep['recommendations']:
        if not r.get('best_action'):
            print(f"  [{r['hardware']}] {r.get('status')} — {r.get('note')}")
            continue
        top = (r.get('routes') or [{}])[0]
        print(f"  [{r['hardware']}] best={r['best_action']}"
              f" net=${top.get('net_profit_usd_day')}/day"
              f" (pred {r.get('prediction_hash')}, {r.get('date')})")
    for u in rep.get('unmatched', []):
        print(f"  [?] {u['kind']} '{u['name']}' — {u['note']}")

    out = args.out or os.path.join(
        BASE_DIR, 'warehouse', 'homelab',
        f"report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{inv['fingerprint']}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(rep, f, indent=2, default=str)
    print(f"[SAVED] {out}")


if __name__ == '__main__':
    main()
