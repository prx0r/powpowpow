"""
Cross-venue factor table — built from daily STATE, not stale snapshots.

Each row is measured from warehouse daily_state (mid closes, depth,
spreads, trade flow) joined to chain fundamentals (emission). Fields
that are still assumed carry an explicit methodology flag; nothing
silently inherits the old hardcoded 0.6 sell fraction.

Also merges the latest derived_signal per asset when present.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402

CHAINS_DIR = os.path.join(BASE_DIR, 'chains')
FACTORS_DIR = os.path.join(CHAINS_DIR, 'factors')
os.makedirs(FACTORS_DIR, exist_ok=True)

CALCULATION_VERSION = "factors-state-v1"


def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def read_states(date):
    rows = []
    for chain in ('venue', 'safetrade'):
        for f in glob.glob(os.path.join(
                BASE_DIR, 'warehouse', 'normalized', 'daily_state',
                f'chain={chain}', 'date=*', 'hour=*.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if r.get('date') == date:
                        rows.append(r)
    return rows


def read_signals(date):
    sigs = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'derived_signal',
            'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get('date') == date and r.get('signal') == 'miner_pressure':
                    sigs[r.get('asset')] = r
    return sigs


def compute_factors(date=None):
    date = date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"\n{'='*60}")
    print(f"Computing Factors from STATE — {date}")
    print(f"{'='*60}")

    fund_all = load_json('chain_fundamentals.json')
    states = read_states(date)
    sigs = read_signals(date)

    by_sym = {}
    for s in states:
        sym = (s.get('symbol') or '').upper()
        a = by_sym.setdefault(sym, {'bid': 0.0, 'ask': 0.0, 'spreads': [],
                                    'close': None, 'buy': 0.0, 'sell': 0.0,
                                    'vol': 0.0, 'trades': 0, 'venues': set(),
                                    'gaps': 0})
        a['bid'] += s.get('bid_notional_20_mean') or 0
        a['ask'] += s.get('ask_notional_20_mean') or 0
        if s.get('spread_bps_median') is not None:
            a['spreads'].append(s['spread_bps_median'])
        if s.get('mid_close'):
            a['close'] = s['mid_close']
        a['buy'] += s.get('trade_buy_notional') or 0
        a['sell'] += s.get('trade_sell_notional') or 0
        a['vol'] += s.get('trade_notional_sum') or 0
        a['trades'] += s.get('n_trades') or 0
        a['venues'].add(s.get('venue'))
        a['gaps'] += s.get('gap_events') or 0

    factors = {}
    try:
        _netstate = json.load(open(os.path.join(BASE_DIR, 'chains', 'network_state.json')))
    except OSError:
        _netstate = {}
    for sym, a in sorted(by_sym.items()):
        fund = fund_all.get(sym, {}) or {}
        emission = fund.get('daily_emission')
        emission_src = f"chain_fundamentals.json:{sym}.daily_emission" if emission else None
        if not emission:
            # Fallback order mirrors signals.load_emission: live measured
            # deltas first (KAS/AKT supply-delta, BTC deterministic).
            live = (_netstate.get(sym, {}) or {})
            for key in ('daily_emission_delta', 'daily_emission'):
                if live.get(key):
                    emission = live[key]
                    emission_src = f"network_state.json:{sym}.{key}"
                    break
        price = a['close']
        emission_usd = emission * price if emission and price else None
        sig = sigs.get(sym, {})
        row = {
            'timestamp': utcnow(),
            'calculation_version': CALCULATION_VERSION,
            'date': date,
            'symbol': sym,
            'name': fund.get('name'),
            'chain_type': fund.get('type'),
            'venues': sorted(a['venues']),
            # Measured from STATE
            'price_usd': price,
            'bid_notional_20_sum': round(a['bid'], 2),
            'ask_notional_20_sum': round(a['ask'], 2),
            'spread_bps_median': (sorted(a['spreads'])[len(a['spreads']) // 2]
                                  if a['spreads'] else None),
            'trade_notional_24h': round(a['vol'], 2),
            'trade_buy_notional': round(a['buy'], 2),
            'trade_sell_notional': round(a['sell'], 2),
            'trade_count_24h': a['trades'],
            'gap_events_24h': a['gaps'],
            # Emission-joined (needs fundamentals price coverage)
            'daily_emission_native': emission,
            'emission_source': emission_src,
            'issuance_usd_24h': round(emission_usd, 2) if emission_usd else None,
            'burden_vs_book': round(emission_usd / a['bid'], 3)
            if emission_usd and a['bid'] > 0 else None,
            'issuance_to_volume': round(emission_usd / a['vol'], 3)
            if emission_usd and a['vol'] > 0 else None,
            # Assumed until miner-flow measurement (disclosed, not hidden)
            'sell_fraction': None,
            'sell_methodology': 'unmeasured — miner exchange flow not yet observed; '
                                'see signals.py assumptions',
            # Signal join
            'miner_pressure': sig.get('direction'),
            'miner_pressure_strength': sig.get('strength'),
            'miner_pressure_version': sig.get('version'),
            # Static context
            'max_supply': fund.get('max_supply'),
            'mining_algo': fund.get('mining_algo'),
            'useful_output': fund.get('useful_output'),
        }
        factors[sym] = row
        iss = f"${row['issuance_usd_24h']:,.0f}/d" if row['issuance_usd_24h'] else "n/a"
        bur = f"{row['burden_vs_book']:.1f}x" if row['burden_vs_book'] else "n/a"
        print(f"  {sym:6} {iss:>14} burden={bur:>8} "
              f"spread={str(row['spread_bps_median']):>8} sig={row['miner_pressure']} "
              f"[{','.join(row['venues'])}]")

    output_file = os.path.join(FACTORS_DIR, 'cross_chain_factors.json')
    with open(output_file, 'w') as f:
        json.dump(factors, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file} ({len(factors)} symbols)")
    return factors


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    compute_factors(args.date)
