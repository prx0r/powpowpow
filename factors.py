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
from signals import (  # noqa: E402
    MIN_BID_USD,
    depth_venues_are_primary,
    load_quote_prices,
    split_symbol,
    to_usd,
)

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
        if (s.get('trade_notional_sum') or s.get('trade_buy_notional')
                or s.get('trade_sell_notional')) and s.get('venue'):
            a.setdefault('trade_venues', set()).add(s['venue'])

    factors = {}
    try:
        _netstate = json.load(open(os.path.join(BASE_DIR, 'chains', 'network_state.json')))
    except OSError:
        _netstate = {}
    # daily_state notionals are quote-currency: a BTC-quoted book reports BTC,
    # not USD. Convert here so every published number is USD-denominated.
    quote_prices = load_quote_prices(BASE_DIR)
    for sym, a in sorted(by_sym.items()):
        base, quote = split_symbol(sym)
        fund = fund_all.get(base, {}) or {}
        emission = fund.get('daily_emission')
        emission_src = f"chain_fundamentals.json:{base}.daily_emission" if emission else None
        if not emission:
            # Fallback order mirrors signals.load_emission: live measured
            # deltas first (KAS/AKT supply-delta, BTC deterministic).
            live = (_netstate.get(base, {}) or {})
            for key in ('daily_emission_delta', 'daily_emission'):
                if live.get(key):
                    emission = live[key]
                    emission_src = f"network_state.json:{base}.{key}"
                    break
        price_native = a['close']
        price = to_usd(price_native, quote, quote_prices)
        bid = to_usd(a['bid'], quote, quote_prices)
        ask = to_usd(a['ask'], quote, quote_prices)
        vol = to_usd(a['vol'], quote, quote_prices)
        buy = to_usd(a['buy'], quote, quote_prices)
        sell = to_usd(a['sell'], quote, quote_prices)
        usd_known = price is not None
        emission_usd = emission * price if emission and price else None
        sig = sigs.get(sym, {})
        row = {
            'timestamp': utcnow(),
            'calculation_version': CALCULATION_VERSION,
            'date': date,
            'symbol': sym,
            'chain_symbol': base,
            'quote_currency': quote,
            'name': fund.get('name'),
            'chain_type': fund.get('type'),
            'venues': sorted(a['venues']),
            'trade_venues': sorted(a.get('trade_venues') or []),
            # Measured from STATE (USD-converted)
            'price_usd': price,
            'price_native': price_native,
            'usd_conversion': 'ok' if usd_known else 'unavailable: quote price unknown',
            'bid_notional_20_sum': round(bid, 2) if bid is not None else None,
            'ask_notional_20_sum': round(ask, 2) if ask is not None else None,
            'spread_bps_median': (sorted(a['spreads'])[len(a['spreads']) // 2]
                                  if a['spreads'] else None),
            'trade_notional_24h': round(vol, 2) if vol is not None else None,
            'trade_buy_notional': round(buy, 2) if buy is not None else None,
            'trade_sell_notional': round(sell, 2) if sell is not None else None,
            'trade_count_24h': a['trades'],
            'gap_events_24h': a['gaps'],
            # Emission-joined (needs fundamentals price coverage)
            'daily_emission_native': emission,
            'emission_source': emission_src,
            'issuance_usd_24h': round(emission_usd, 2) if emission_usd else None,
            'burden_vs_book': round(emission_usd / bid, 3)
            if emission_usd and bid else None,
            'issuance_to_volume': round(emission_usd / vol, 3)
            if emission_usd and vol else None,
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
    prior = {}
    if os.path.exists(output_file):
        try:
            with open(output_file) as f:
                prior = json.load(f)
        except (OSError, ValueError):
            prior = {}

    # Chain rows aggregate every pair instead of aliasing one preferred pair:
    # PRL's USDC book (73% of its resting bids) used to be invisible because
    # the USDT row won the alias. All sums are already USD-denominated.
    groups = {}
    for sym, row in factors.items():
        base = row.get('chain_symbol')
        if not base or base == sym:
            continue
        groups.setdefault(base, []).append(row)

    def _preference(row):
        symbol = row.get('symbol') or ''
        return 3 if symbol.endswith('USDT') else (2 if symbol.endswith('USDC') else 1)

    for base, rows in groups.items():
        primary = max(rows, key=_preference)
        contributing = [r for r in rows if (r.get('bid_notional_20_sum') or 0) > 0]
        bid = sum(r['bid_notional_20_sum'] for r in contributing) or None
        ask = sum(r.get('ask_notional_20_sum') or 0 for r in rows) or None
        vol = sum(r.get('trade_notional_24h') or 0 for r in rows) or None
        spreads = [r['spread_bps_median'] for r in rows
                   if r.get('spread_bps_median') is not None]
        venues = sorted({v for r in rows for v in (r.get('venues') or [])})
        issuance = primary.get('issuance_usd_24h')
        sig = sigs.get(base, {})
        burden = round(issuance / bid, 3) if issuance and bid else None
        to_vol = round(issuance / vol, 3) if issuance and vol else None
        trade_venues = sorted({v for r in rows
                               for v in (r.get('trade_venues') or [])})
        refusal = None
        if not depth_venues_are_primary(base, trade_venues):
            # Prints are SafeTrade-only, so measured volume is not the market's.
            to_vol = None
        if not depth_venues_are_primary(base, venues):
            # Denominator measures SafeTrade, not the market where this chain
            # trades — publish the refusal instead of a fake ratio.
            burden = to_vol = None
            refusal = ('depth_not_venue_of_truth: ' + ','.join(venues))
        elif bid and bid < MIN_BID_USD:
            # A book this thin is indistinguishable from an empty one.
            burden = to_vol = None
            refusal = (f'bid_below_resolution (${bid:,.0f} < '
                       f'${MIN_BID_USD:,.0f})')
        factors.setdefault(base, {
            'timestamp': utcnow(),
            'calculation_version': CALCULATION_VERSION,
            'date': date,
            'symbol': base,
            'chain_symbol': base,
            'venue_symbol': primary.get('symbol'),
            'quote_currency': primary.get('quote_currency'),
            'name': primary.get('name'),
            'chain_type': primary.get('chain_type'),
            'venues': venues,
            'trade_venues': trade_venues,
            'depth_pairs': [r.get('symbol') for r in contributing],
            'price_usd': primary.get('price_usd'),
            'bid_notional_20_sum': round(bid, 2) if bid is not None else None,
            'ask_notional_20_sum': round(ask, 2) if ask is not None else None,
            'spread_bps_median': (sorted(spreads)[len(spreads) // 2]
                                  if spreads else None),
            'trade_notional_24h': round(vol, 2) if vol is not None else None,
            'trade_buy_notional': round(sum(r.get('trade_buy_notional') or 0
                                            for r in rows), 2),
            'trade_sell_notional': round(sum(r.get('trade_sell_notional') or 0
                                             for r in rows), 2),
            'trade_count_24h': sum(r.get('trade_count_24h') or 0 for r in rows),
            'gap_events_24h': sum(r.get('gap_events_24h') or 0 for r in rows),
            'daily_emission_native': primary.get('daily_emission_native'),
            'emission_source': primary.get('emission_source'),
            'issuance_usd_24h': issuance,
            'burden_vs_book': burden,
            'issuance_to_volume': to_vol,
            'market_coverage_refusal': refusal,
            'sell_fraction': primary.get('sell_fraction'),
            'sell_methodology': primary.get('sell_methodology'),
            'miner_pressure': sig.get('direction') or primary.get('miner_pressure'),
            'miner_pressure_strength': (sig.get('strength')
                                        or primary.get('miner_pressure_strength')),
            'miner_pressure_version': (sig.get('version')
                                       or primary.get('miner_pressure_version')),
            'max_supply': primary.get('max_supply'),
            'mining_algo': primary.get('mining_algo'),
            'useful_output': primary.get('useful_output'),
        })

    carried = 0
    for base, row in prior.items():
        if base in factors or not isinstance(row, dict):
            continue
        factors[base] = dict(row, carried_forward=True,
                             carried_forward_at=row.get('timestamp'))
        carried += 1

    with open(output_file, 'w') as f:
        json.dump(factors, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file} ({len(factors)} symbols, "
          f"{len(groups)} chain rows aggregated, {carried} carried forward)")
    return factors


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    compute_factors(args.date)
