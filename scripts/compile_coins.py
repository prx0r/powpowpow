"""
Knowledge compiler seed — coin pages compiled from the graph, not handwritten.

Per symbol: registry identity + fundamentals + latest STATE (all venues) +
latest derived signal + factor row. Rerun anytime; pages are projections
of the garden at generation time (stamped + provenance-linked).

Usage:
    python3 scripts/compile_coins.py
Output:
    pages/<SYM>.md
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PAGES_DIR = os.path.join(BASE_DIR, 'pages')
os.makedirs(PAGES_DIR, exist_ok=True)


def latest(table, key_fn, chain_options=('venue', 'safetrade')):
    best = {}
    for chain in chain_options:
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', table,
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    k = key_fn(r)
                    if not k:
                        continue
                    cur = best.get(k)
                    stamp = r.get('receive_time') or r.get('generated_at') or r.get('date', '')
                    if cur is None or stamp > cur[0]:
                        best[k] = (stamp, r)
    return {k: v[1] for k, v in best.items()}


def main():
    sys.path.insert(0, BASE_DIR)
    from v1_registry import get_v1
    fund = json.load(open(os.path.join(BASE_DIR, 'chains', 'chain_fundamentals.json')))
    try:
        factors = json.load(open(os.path.join(BASE_DIR, 'chains', 'factors', 'cross_chain_factors.json')))
    except OSError:
        factors = {}

    states, sigs = {}, {}
    for f in glob.glob(os.path.join(BASE_DIR, 'warehouse', 'normalized', 'daily_state',
                                    'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                k = (r.get('symbol'), r.get('venue'))
                cur = states.get(k)
                if cur is None or (r.get('date', '') > cur.get('date', '')):
                    states[k] = r
    for f in glob.glob(os.path.join(BASE_DIR, 'warehouse', 'normalized', 'derived_signal',
                                    'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                a = r.get('asset')
                if a and (a not in sigs or r.get('date', '') > sigs[a].get('date', '')):
                    sigs[a] = r

    v1 = get_v1()
    symbols = sorted(set(list(v1) + list(fund)))
    now = datetime.now(timezone.utc).isoformat()
    for sym in symbols:
        reg = v1.get(sym, {})
        f = fund.get(sym, {}) or {}
        fac = factors.get(sym, {}) or {}
        sig = sigs.get(sym, {})
        lines = [f"# {sym} — compiled {now}", ""]
        lines.append(f"*{f.get('name', reg.get('name', sym))} — "
                     f"{reg.get('category', f.get('type', 'research-universe'))}*")
        lines.append("")
        lines.append("## Identity")
        for k in ('physical_resource', 'resource_type', 'supplier_type', 'telemetry',
                  'marginal_cost', 'reward', 'supply_response', 'price_source'):
            if reg.get(k):
                lines.append(f"- {k}: {reg[k]}")
        for k in ('mining_algo', 'useful_output', 'hardware', 'consensus',
                  'max_supply', 'daily_emission', 'github'):
            if f.get(k) is not None:
                lines.append(f"- {k}: {f[k]}")
        lines.append("")
        lines.append("## Current economic state (latest STATE per venue)")
        hit = False
        for (s, v), st in sorted(states.items()):
            if s != sym:
                continue
            hit = True
            lines.append(f"- {v} {st.get('date')}: mid_close={st.get('mid_close')} "
                         f"spread_med={st.get('spread_bps_median')} "
                         f"trades={st.get('n_trades')} gaps={st.get('gap_events')}")
        if not hit:
            lines.append("- no STATE coverage yet")
        lines.append("")
        lines.append("## Derived signal")
        if sig:
            lines.append(f"- {sig.get('signal')} {sig.get('version')}: "
                         f"{sig.get('direction')} ({sig.get('strength')}) on {sig.get('date')}")
            lines.append(f"- drivers: {'; '.join(sig.get('drivers', []))}")
            lines.append(f"- assumptions: {'; '.join(sig.get('assumptions', []))}")
        else:
            lines.append("- none (insufficient emission/price/depth coverage)")
        lines.append("")
        lines.append("## Factor row")
        for k in ('issuance_usd_24h', 'burden_vs_book', 'issuance_to_volume',
                  'trade_notional_24h', 'venues'):
            if fac.get(k) is not None:
                lines.append(f"- {k}: {fac[k]}")
        lines.append("")
        lines.append(f"*Projection of the garden at {now}. Regenerate with "
                     f"`scripts/compile_coins.py`. Provenance: warehouse record IDs.*")
        with open(os.path.join(PAGES_DIR, f'{sym}.md'), 'w') as fh:
            fh.write('\n'.join(lines) + '\n')
    print(f"[COMPILE] {len(symbols)} pages -> {PAGES_DIR}/")


if __name__ == '__main__':
    main()
