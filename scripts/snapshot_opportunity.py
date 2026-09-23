"""
Opportunity snapshot — the daily counterfactual record (todo.md #13/#14).

For each hardware archetype, ranks every route (mine each coin, rent,
idle) by expected net USD/day and records the full ranked set BEFORE
outcomes exist. This is the prediction log that later enables
calibration (expected vs realized) and the homelab recommender.

One row per (date, hardware) in normalized `opportunity_snapshot`:
  date, hardware, electricity_usd_kwh, routes[] (ranked),
  best_action, model_version, code_hash, prediction_hash,
  price_evidence (STATE record IDs), generated_at.

Prediction hash = sha256 over canonical (date, hardware, rounded nets,
model_version). v1: local hash only; OpenTimestamps anchoring is future.

Usage:
    python3 scripts/snapshot_opportunity.py --date 2026-09-23
    python3 scripts/snapshot_opportunity.py   # today (UTC)
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import store_normalized, utcnow  # noqa: E402
from v1_live_cards import (  # noqa: E402
    generate_card, V1_HARDWARE, CALCULATION_VERSION,
)

# Market symbol -> asset (longest prefix wins; venue suffixes stripped).
ASSETS = ('PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS', 'CLORE', 'AKT', 'NOS')


def asset_of(market_symbol):
    s = (market_symbol or '').upper()
    for a in sorted(ASSETS, key=len, reverse=True):
        if s == a or s.startswith(a):
            return a
    return None


def code_hash():
    try:
        h = hashlib.sha256()
        for fn in ('v1_live_cards.py', 'scripts/snapshot_opportunity.py'):
            with open(os.path.join(BASE_DIR, fn), 'rb') as f:
                h.update(f.read())
        try:
            rev = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                 capture_output=True, text=True, timeout=5,
                                 cwd=BASE_DIR)
            if rev.returncode == 0:
                h.update(rev.stdout.strip().encode())
        except Exception:
            pass
        return h.hexdigest()[:16]
    except OSError:
        return 'unknown'


def latest_asset_prices(date=None):
    """Latest mid per asset from daily STATE + evidence record IDs."""
    best = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'daily_state',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if date and r.get('date') != date:
                    continue
                asset = asset_of(r.get('symbol'))
                if not asset or not r.get('mid_close'):
                    continue
                stamp = r.get('observed_at', '') or r.get('date', '')
                cur = best.get(asset)
                if cur is None or stamp > cur[0]:
                    best[asset] = (stamp, r['mid_close'], r.get('record_id'),
                                   r.get('venue'), r.get('date'))
    return {a: {'price': v[1], 'record_id': v[2], 'venue': v[3], 'date': v[4]}
            for a, v in best.items()}


def hardware_index():
    """Invert V1_HARDWARE: hardware -> [(coin, specs)]."""
    idx = {}
    for coin, hwmap in V1_HARDWARE.items():
        for hw, specs in (hwmap or {}).items():
            idx.setdefault(hw, []).append((coin, specs))
    return idx


def snapshot(date, electricity=0.10):
    prices = latest_asset_prices(date if date != datetime.now(timezone.utc).strftime('%Y-%m-%d') else None)
    chash = code_hash()
    model_version = f"opportunity-v1+{CALCULATION_VERSION}"
    n = 0
    for hw, coins in sorted(hardware_index().items()):
        routes = []
        for coin, specs in coins:
            p = prices.get(coin, {})
            price = p.get('price', 0)
            try:
                card = generate_card(coin, price, electricity=electricity)
            except Exception as e:
                routes.append({'coin': coin, 'action': f'mine_{coin.lower()}',
                               'error': str(e)[:100]})
                continue
            h = (card.get('hardware') or {}).get(hw, {})
            routes.append({
                'coin': coin,
                'action': f"rent_{coin.lower()}" if h.get('algo') in ('rental', 'inference') else f"mine_{coin.lower()}",
                'algo': h.get('algo'),
                'revenue_usd_day': h.get('revenue_usd_day'),
                'electricity_usd_day': h.get('electricity_usd_day'),
                'hw_amort_usd_day': h.get('hw_amort_usd_day'),
                'net_profit_usd_day': h.get('net_profit_usd_day'),
                'payback_days': h.get('payback_days'),
                'assumption': h.get('assumption'),
                'price_usd': price,
                'price_venue': p.get('venue'),
                'price_evidence': p.get('record_id'),
                'network': card.get('network'),
                'status': card.get('status'),
            })
        # Idle route: explicit zero, always available.
        routes.append({'coin': None, 'action': 'idle', 'algo': 'idle',
                       'revenue_usd_day': 0.0, 'electricity_usd_day': 0.0,
                       'hw_amort_usd_day': 0.0, 'net_profit_usd_day': 0.0,
                       'payback_days': None,
                       'assumption': 'machine off; opportunity cost baseline'})
        ranked = sorted(routes,
                        key=lambda r: (r.get('net_profit_usd_day')
                                       if r.get('net_profit_usd_day') is not None
                                       else float('-inf')),
                        reverse=True)
        best_action = ranked[0]['action'] if ranked else 'idle'
        # Prediction hash over canonical rounded nets.
        canon = json.dumps({
            'date': date, 'hardware': hw,
            'nets': [r.get('net_profit_usd_day') for r in ranked],
            'model': model_version,
        }, sort_keys=True, default=str)
        pred_hash = hashlib.sha256(canon.encode()).hexdigest()[:16]
        store_normalized('opportunity_snapshot', 'venue', {
            'date': date, 'hardware': hw,
            'electricity_usd_kwh': electricity,
            'routes': ranked, 'best_action': best_action,
            'model_version': model_version, 'code_hash': chash,
            'prediction_hash': pred_hash,
            'n_routes': len(ranked),
        }, event_time=date)
        n += 1
        top = ranked[0]
        print(f"  [{hw}] best={top['action']} net={top.get('net_profit_usd_day')} "
              f"({len(ranked)} routes, pred={pred_hash})")
    print(f"[OPPORTUNITY {date}] {n} hardware snapshots")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    ap.add_argument('--electricity', type=float, default=0.10)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    snapshot(date, electricity=args.electricity)


if __name__ == '__main__':
    main()
