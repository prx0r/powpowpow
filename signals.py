"""
Canonical signals v1 — derived measurements with provenance, versioned.

Vision rule: a signal is a graph transformation with provenance, not an
LLM opinion. Every signal carries asset, direction, strength, drivers,
evidence (record IDs), assumptions, confidence, definition version, and
timestamp. Transformations are versioned (miner_pressure_v1 vs v2) and
rerun against immutable history — never overwritten.

miner_pressure_v1 inputs (all measured except where flagged):
  creation burden  = daily emission USD / cross-venue bid notional
  depth thinness   = 1 / total bid notional (relative, cross-sectional)
  illiquidity      = median spread_bps (relative, cross-sectional)
Unmeasured (assumed, disclosed): miner sell fraction / exchange-bound
flow. v1 does NOT pretend to know realization — it scores structural
creation burden vs absorbable liquidity.

Direction comes from the cross-sectional z-score of the burden composite:
coins bearing unusually large fresh-supply-vs-book burdens score bearish.
Strength = logistic(|z|). With <4 markets of data the module refuses
(insufficient cross-section) rather than fabricating.

Usage:
    python3 signals.py --date 2026-09-19
"""

import argparse
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import purge_normalized, store_normalized  # noqa: E402

SIGNAL_VERSION = "miner_pressure_v1"
CALCULATION_VERSION = "signals-v1.0"

QUOTE_SUFFIXES = ('USDT', 'USDC', 'SAFE', 'BTC', 'XMR', 'USD')
USD_QUOTES = ('USDT', 'USDC', 'USD')

# Depth measured on these venues is not that chain's venue of truth: the
# book is a rounding error beside where the coin actually trades (SafeTrade
# top-20 bid = $168 BTC / $29 XMR on 89 / 37 trades a day), so the
# denominator would measure SafeTrade rather than the market. Such a chain
# is scored only once some other venue contributes depth.
SECONDARY_DEPTH_VENUES = {
    'BTC': {'safetrade'},
    'XMR': {'safetrade'},
}

# Below this the top-20 book is indistinguishable from an empty one.
MIN_BID_USD = 100.0


def chain_symbol(symbol):
    """XMRUSDT / PRLBTC / NOCKUSDC -> XMR / PRL / NOCK (lookup key)."""
    s = (symbol or '').upper()
    for quote in QUOTE_SUFFIXES:
        if s.endswith(quote) and len(s) > len(quote):
            return s[:-len(quote)]
    return s


def split_symbol(symbol):
    """PRLBTC -> ('PRL', 'BTC'); XMRUSD -> ('XMR', 'USD'); PRL -> ('PRL', None)."""
    s = (symbol or '').upper()
    for quote in QUOTE_SUFFIXES:
        if s.endswith(quote) and len(s) > len(quote):
            return s[:-len(quote)], quote
    return s, None


def load_quote_prices(base_dir=None):
    """Quote currency -> USD price. USD quotes are 1.0 by definition; BTC/XMR
    come from the factor table's chain rows, falling back to network_state."""
    base_dir = base_dir or BASE_DIR
    prices = {}
    for path, key in (
        (os.path.join(base_dir, 'chains', 'factors',
                       'cross_chain_factors.json'), 'price_usd'),
        (os.path.join(base_dir, 'chains', 'network_state.json'), 'price_usd'),
    ):
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        for name, row in (data or {}).items():
            if isinstance(row, dict) and row.get(key):
                prices.setdefault(chain_symbol(name), row[key])
    return prices


def to_usd(value, quote, prices):
    """Quote-currency amount -> USD, or None when the quote is unknown."""
    if value is None:
        return None
    if quote in USD_QUOTES or quote is None:
        # No quote suffix means venue discovery already gave us a USDT market.
        return value
    px = prices.get(quote)
    if not px:
        return None
    return value * px


def depth_venues_are_primary(chain, venues):
    """True when measured depth comes from a venue that trades this chain."""
    secondary = SECONDARY_DEPTH_VENUES.get(chain)
    if not secondary:
        return True
    return bool({v for v in venues if v and v not in secondary})


def read_states(date, chain='venue'):
    rows = []
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


def load_emission(symbol):
    """Daily native emission lookup. Order: live network_state (engines,
    measured deltas) -> fundamentals -> researched schedules."""
    base = chain_symbol(symbol)
    try:
        live = json.load(open(os.path.join(BASE_DIR, 'chains', 'network_state.json')))
        for key in ('daily_emission_delta', 'daily_emission'):
            entry = (live.get(base, {}) or {})
            if entry.get(key):
                return entry[key], f"network_state.json:{base}.{key}"
    except OSError:
        pass
    try:
        fund = json.load(open(os.path.join(BASE_DIR, 'chains', 'chain_fundamentals.json')))
    except OSError:
        fund = {}
    e = (fund.get(base, {}) or {}).get('daily_emission')
    if e:
        return e, f"chain_fundamentals.json:{base}.daily_emission"
    try:
        from emission import estimate as emission_estimate
        est, prov = emission_estimate(base)
        if est:
            return est, f"emission.py:{base} ({prov.get('source', '')} [{prov.get('confidence', '')}])"
    except Exception:
        pass
    return None, "unknown"


def zscore(xs):
    n = len(xs)
    if n < 2:
        return [0.0] * n
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    sd = math.sqrt(var) or 1e-12
    return [(x - m) / sd for x in xs]


def logistic(x):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def aggregate_chains(date):
    """Chain-level USD view of daily_state across every pair and venue.

    Depth, flow and volume are summed only after quote -> USD conversion, so a
    BTC-quoted book is never added to a USDT one. Price prefers a USD-quoted
    pair; the latest converted close is the fallback.
    """
    states = read_states(date) + read_states(date, 'safetrade')
    prices = load_quote_prices()
    agg = {}
    for s in states:
        sym = (s.get('symbol') or '').upper()
        chain, quote = split_symbol(sym)
        if not chain:
            continue
        a = agg.setdefault(chain, {
            'bid': 0.0, 'ask': 0.0, 'spreads': [], 'records': [],
            'trades_n': 0, 'vol': 0.0, 'buy': 0.0, 'sell': 0.0,
            'pairs': set(), 'venues': set(), 'depth_venues': set(),
            'trade_venues': set(), 'usd_close': None, 'any_close': None,
        })
        venue = s.get('venue')
        a['pairs'].add(sym)
        if venue:
            a['venues'].add(venue)
        bid = to_usd(s.get('bid_notional_20_mean'), quote, prices)
        if bid:
            a['bid'] += bid
            if venue:
                a['depth_venues'].add(venue)
        ask = to_usd(s.get('ask_notional_20_mean'), quote, prices)
        if ask:
            a['ask'] += ask
        if s.get('spread_bps_median') is not None:
            a['spreads'].append(s['spread_bps_median'])
        vol_usd = to_usd(s.get('trade_notional_sum'), quote, prices) or 0.0
        buy_usd = to_usd(s.get('trade_buy_notional'), quote, prices) or 0.0
        sell_usd = to_usd(s.get('trade_sell_notional'), quote, prices) or 0.0
        a['vol'] += vol_usd
        a['buy'] += buy_usd
        a['sell'] += sell_usd
        if (vol_usd or buy_usd or sell_usd) and venue:
            # flow claims need a venue that actually trades the chain
            a['trade_venues'].add(venue)
        a['trades_n'] += s.get('n_trades', 0) or 0
        if s.get('record_id'):
            a['records'].append(s['record_id'])
        mid = to_usd(s.get('mid_close'), quote, prices)
        if mid:
            stamp = s.get('observed_at') or s.get('coverage_last') or ''
            candidate = (stamp, mid)
            if quote in USD_QUOTES:
                if a['usd_close'] is None or stamp >= a['usd_close'][0]:
                    a['usd_close'] = candidate
            elif a['any_close'] is None or stamp >= a['any_close'][0]:
                a['any_close'] = candidate
    return agg


def chain_price(agg_row):
    """USD price for a chain: USD-quoted pair preferred, converted fallback."""
    close = agg_row['usd_close'] or agg_row['any_close']
    return close[1] if close else None


def venue_reason(chain, agg_row, field='depth_venues'):
    """Refuse chain-level claims made from a venue that is not the market.

    `field` selects which claim is being checked: depth-based (burden) or
    trade-based (flow/coverage). A chain can pass one and fail the other —
    BTC's depth now comes from Coinbase/Kraken while its prints are still
    SafeTrade-only.
    """
    venues = agg_row.get(field) or set()
    if not venues:
        return None  # no contribution to gate on; caller reports absence first
    if not depth_venues_are_primary(chain, venues):
        return (f'{field[:-7] if field.endswith("_venues") else field}'
                f'_not_venue_of_truth: ' + ','.join(sorted(venues)))
    return None


def burden_reason(chain, agg_row):
    """Refuse burden claims that would be measured off an unusable book."""
    if agg_row['bid'] <= 0:
        return 'no_depth'
    if agg_row['bid'] < MIN_BID_USD:
        return (f'bid_below_resolution '
                f'(${agg_row["bid"]:,.0f} < ${MIN_BID_USD:,.0f})')
    return venue_reason(chain, agg_row)


def build_signals(date):
    agg = aggregate_chains(date)

    # Measured burden per chain (needs emission + USD price + depth).
    scored = []
    refusals = {}
    for chain, a in sorted(agg.items()):
        emission, emission_src = load_emission(chain)
        price = chain_price(a)
        if not emission:
            refusals[chain] = 'no_emission'
            continue
        if price is None:
            refusals[chain] = 'no_usd_price'
            continue
        reason = burden_reason(chain, a)
        if reason:
            refusals[chain] = reason
            continue
        emission_usd = emission * price
        burden = emission_usd / a['bid']  # days of book to absorb one day of supply
        spread_med = sorted(a['spreads'])[len(a['spreads']) // 2] if a['spreads'] else None
        scored.append({'symbol': chain, 'burden': burden,
                       'emission_usd': emission_usd, 'bid': a['bid'],
                       'ask': a['ask'], 'vol': a['vol'],
                       'spread_med': spread_med, 'states': a['records'],
                       'emission_src': emission_src, 'trades_n': a['trades_n'],
                       'venues': sorted(v for v in a['depth_venues'] if v),
                       'pairs': sorted(a['pairs']),
                       'venue_of_truth': True})

    for chain, reason in sorted(refusals.items()):
        print(f"[SIGNALS {date}] refused {chain}: {reason}")

    if len(scored) < 4:
        print(f"[SIGNALS {date}] insufficient cross-section ({len(scored)} markets) — refusing")
        return []

    zs = zscore([math.log10(max(s['burden'], 1e-12)) for s in scored])
    out = []
    for s, z in zip(scored, zs):
        direction = 'bearish' if z > 0.5 else ('bullish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        drivers = [
            f"emission_usd_day={s['emission_usd']:,.0f}",
            f"bid_notional_20_sum={s['bid']:,.0f}",
            f"burden={s['burden']:.2f}x",
        ]
        if s['spread_med'] is not None:
            drivers.append(f"spread_bps_med={s['spread_med']:.1f}")
        sig = {
            'asset': s['symbol'],
            'signal': 'miner_pressure',
            'version': SIGNAL_VERSION,
            'calculation_version': CALCULATION_VERSION,
            'direction': direction,
            'strength': strength,
            'burden_z': round(z, 3),
            'drivers': drivers,
            'evidence': {'daily_state_records': s['states'],
                         'emission_source': s['emission_src'],
                         'depth_venues': s['venues'],
                         'depth_pairs': s['pairs']},
            'assumptions': [
                'sell_fraction unmeasured: burden is structural creation load, '
                'not observed miner selling',
                'bid_notional_20 is top-20-level resting notional, not full book',
                'depth summed to chain level across pairs and venues, converted '
                'quote -> USD (USD quotes = 1.0, BTC/XMR priced from the factor '
                'table); symbols without a quote suffix count as USDT',
                'BTC/XMR depth sourced only from SafeTrade is refused: that book '
                'is not the market (see SECONDARY_DEPTH_VENUES)',
            ],
            'confidence': 'medium' if s['trades_n'] > 50 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['burden_z'], reverse=True)
    return out


FLOW_VERSION = "flow_pressure_v1"


def build_flow_signals(date):
    """flow_pressure_v1: measured venue trade flow vs resting book.

    absorption = buy_notional / sell_notional (24h, cross-venue).
    sell_load  = sell_notional / bid_notional_20 (can the book take it?).
    Direction from cross-sectional z of net-flow-imbalance; strength
    logistic. Disclosed: venue flow only (CoinEx+Gate), NOT miner-attributed.
    """
    states = aggregate_chains(date)
    scored = []
    refusals = {}
    for chain, a in sorted(states.items()):
        tot = a['buy'] + a['sell']
        if tot <= 0 or a['trades_n'] < 5:
            refusals[chain] = 'no_flow' if tot <= 0 else 'too_few_trades'
            continue
        reason = venue_reason(chain, a, 'trade_venues')
        if reason:
            refusals[chain] = reason
            continue
        imb = (a['buy'] - a['sell']) / tot
        sell_load = a['sell'] / a['bid'] if a['bid'] > 0 else None
        scored.append({'symbol': chain, 'imb': imb, 'sell_load': sell_load,
                       'buy': a['buy'], 'sell': a['sell'],
                       'records': a['records'], 'trades': a['trades_n'],
                       'venues': sorted(v for v in a['trade_venues'] if v),
                       'pairs': sorted(a['pairs'])})
    for chain, reason in sorted(refusals.items()):
        print(f"[FLOW {date}] refused {chain}: {reason}")
    if len(scored) < 4:
        print(f"[FLOW {date}] insufficient cross-section ({len(scored)}) — refusing")
        return []
    zs = zscore([s['imb'] for s in scored])
    out = []
    for s, z in zip(scored, zs):
        direction = 'bullish' if z > 0.5 else ('bearish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        sig = {
            'asset': s['symbol'], 'signal': 'flow_pressure',
            'version': FLOW_VERSION, 'calculation_version': CALCULATION_VERSION,
            'direction': direction, 'strength': strength,
            'imbalance_z': round(z, 3),
            'drivers': [f"buy_notional={s['buy']:,.0f}",
                        f"sell_notional={s['sell']:,.0f}",
                        f"sell_load_vs_book={s['sell_load']:.2f}x"
                        if s['sell_load'] else "sell_load_vs_book=n/a"],
            'evidence': {'daily_state_records': s['records'],
                         'depth_venues': s['venues'],
                         'depth_pairs': s['pairs']},
            'assumptions': ['venue trade flow only (CoinEx+Gate); not '
                            'miner-attributed until pool graph exists',
                            'thin-history: single-day flow window',
                            'buy/sell summed to chain level across pairs and '
                            'venues after quote -> USD conversion'],
            'confidence': 'medium' if s['trades'] > 100 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['imbalance_z'])
    return out


REQ_VERSION = "required_flow_v1"


def build_required_signals(date):
    """required_flow_v1: how much buying the day needed to stand still.

    required = emission_usd + sell_notional - buy_notional (floored 0).
    coverage = buy / (emission_usd + sell). Bearish when buying covered
    little of the structural + realized load. Limit-order add/cancel flow
    is unmeasured at daily grain — disclosed, not faked.
    """
    groups = aggregate_chains(date)
    scored = []
    refusals = {}
    for chain, a in sorted(groups.items()):
        emission, esrc = load_emission(chain)
        price = chain_price(a)
        if not emission:
            refusals[chain] = 'no_emission'
            continue
        if price is None:
            refusals[chain] = 'no_usd_price'
            continue
        if a['trades_n'] < 5:
            refusals[chain] = f"too_few_trades ({a['trades_n']} < 5)"
            continue
        reason = venue_reason(chain, a, 'trade_venues')
        if reason:
            refusals[chain] = reason
            continue
        em_usd = emission * price
        required = max(0.0, em_usd + a['sell'] - a['buy'])
        denom = em_usd + a['sell']
        coverage = a['buy'] / denom if denom > 0 else None
        scored.append({'symbol': chain, 'required': required,
                       'coverage': coverage, 'em_usd': em_usd,
                       'buy': a['buy'], 'sell': a['sell'],
                       'records': a['records'], 'esrc': esrc,
                       'trades': a['trades_n']})
    for chain, reason in sorted(refusals.items()):
        print(f"[REQ {date}] refused {chain}: {reason}")
    if len(scored) < 4:
        print(f"[REQ {date}] insufficient cross-section ({len(scored)}) — refusing")
        return []
    covs = [s['coverage'] for s in scored if s['coverage'] is not None]
    zs = zscore(covs)
    out = []
    for s, z in zip([x for x in scored if x['coverage'] is not None], zs):
        direction = 'bullish' if z > 0.5 else ('bearish' if z < -0.5 else 'neutral')
        strength = round(logistic(abs(z) - 0.5) if direction != 'neutral'
                         else logistic(abs(z)) * 0.5, 3)
        sig = {
            'asset': s['symbol'], 'signal': 'required_flow',
            'version': REQ_VERSION, 'calculation_version': CALCULATION_VERSION,
            'direction': direction, 'strength': strength,
            'coverage_z': round(z, 3),
            'drivers': [f"required_buy_usd={s['required']:,.0f}",
                        f"coverage={s['coverage']:.2f}",
                        f"emission_usd={s['em_usd']:,.0f}"],
            'evidence': {'daily_state_records': s['records'],
                         'emission_source': s['esrc']},
            'assumptions': ['miner sells proxied by full emission (upper bound); '
                            'realization unmeasured',
                            'limit add/cancel flow unmeasured at daily grain',
                            'buy/sell summed to chain level after quote -> USD '
                            'conversion'],
            'confidence': 'medium' if s['trades'] > 100 else 'low-data',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'date': date,
        }
        out.append(sig)
        store_normalized('derived_signal', 'venue', sig, event_time=date)
    out.sort(key=lambda s: s['coverage_z'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    purged = purge_normalized('derived_signal', 'date', date)
    if purged:
        print(f"[SIGNALS {date}] purged {purged} prior rows for idempotent rebuild")
    sigs = build_signals(date)
    for s in sigs:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s.get('burden_z', s.get('imbalance_z')):+.2f} | {' '.join(s['drivers'])}")
    print(f"[SIGNALS {date}] {len(sigs)} signals ({SIGNAL_VERSION})")
    flows = build_flow_signals(date)
    for s in flows:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s['imbalance_z']:+.2f} | {' '.join(s['drivers'])}")
    print(f"[FLOW {date}] {len(flows)} signals ({FLOW_VERSION})")
    reqs = build_required_signals(date)
    for s in reqs:
        print(f"  {s['asset']:6} {s['signal']:14} {s['direction']:8} {s['strength']:.2f} "
              f"z={s['coverage_z']:+.2f} | {' '.join(s['drivers'])}")
    print(f"[REQ {date}] {len(reqs)} signals ({REQ_VERSION})")


if __name__ == '__main__':
    main()
