"""
BTC context — the M0 baseline + security-spend reference.

Reads 365d closes (BTC + XMR/QUBIC) from price_history and computes,
stdlib-only:
  - log returns, rolling BTC betas (30d/90d), residual returns
  - BTC security spend series (450 BTC/day x price + fees where joined)
  - content hook: "X up N%, only M% explained by BTC"

Output: warehouse/btc_context.json. Every number cites inputs.
No sklearn/pandas: covariance/variance by hand, disclosed.

Usage:
    python3 scripts/btc_context.py
"""

import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow  # noqa: E402

BTC_EMISSION_DAY = 450.0  # 3.125 BTC/block x ~144 blocks/day, post-halving


def load_closes(sym):
    out = []
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'price_history',
            f'chain={sym.lower()}', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('close_usd'):
                    out.append((r['date'], float(r['close_usd'])))
    out.sort()
    # De-dupe dates, keep last.
    ded = {}
    for d, c in out:
        ded[d] = c
    return sorted(ded.items())


def log_returns(closes):
    return [(closes[i][0], math.log(closes[i][1] / closes[i - 1][1]))
            for i in range(1, len(closes)) if closes[i - 1][1] > 0]


def rolling_beta(asset_rets, btc_rets, window):
    """Beta + residual series. Refuses when < window overlap."""
    bmap = dict(btc_rets)
    paired = [(d, a, bmap[d]) for d, a in asset_rets if d in bmap]
    out = []
    for i in range(window, len(paired)):
        win = paired[i - window:i]
        xs = [p[2] for p in win]
        ys = [p[1] for p in win]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        beta = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
                if den else None)
        d, a, b = paired[i]
        out.append({'date': d, 'beta': round(beta, 3) if beta is not None else None,
                    'asset_ret': round(a, 5), 'btc_ret': round(b, 5),
                    'residual': round(a - beta * b, 5) if beta is not None else None})
    return out


def main():
    btc = load_closes('BTC')
    if len(btc) < 40:
        print(f"[BTC CONTEXT] insufficient BTC history ({len(btc)} closes)")
        return {}
    btc_rets = log_returns(btc)
    prices = [c for _, c in btc]
    lo, hi, cur = min(prices), max(prices), prices[-1]
    try:
        net = json.load(open(os.path.join(BASE_DIR, 'chains', 'network_state.json'))).get('BTC', {})
    except OSError:
        net = {}
    height = net.get('height') or net.get('tip_height_crosscheck') or 0
    epoch = height // 210000 if height else None
    ctx = {'computed_at': utcnow(), 'btc_closes': len(btc),
           'btc_price': btc[-1][1], 'btc_date': btc[-1][0],
           'btc_emission_day': BTC_EMISSION_DAY,
           'btc_security_spend_usd_day': round(BTC_EMISSION_DAY * btc[-1][1], 0),
           'price_position_365d': {
               'current': cur, 'low': lo, 'high': hi,
               'percentile': round(sum(1 for p in prices if p <= cur) / len(prices) * 100, 1),
               'range': f"${lo:,.0f} - ${hi:,.0f}",
           },
           'halving': {
               'height': height,
               'epoch': epoch,
               'subsidy': round(50 / 2**epoch, 4) if epoch is not None else None,
               'next_halving_height': (epoch + 1) * 210000 if epoch is not None else None,
               'blocks_remaining': (epoch + 1) * 210000 - height if epoch is not None else None,
           },
           'retarget': {
               'next_retarget': net.get('next_retarget'),
               'progress': round((height % 2016) / 2016, 3) if height else None,
           },
           'fees': {
               # NOTE: blockchain.info stats total_fees_btc returns negative
               # values (verified 2026-09-23) — untrustworthy, dropped.
               # Fee truth = transaction-fees-usd chart history + live estimates.
               'mempool_txs': net.get('mempool_txs'),
               'fee_next_block_satvb': net.get('fee_next_block_satvb'),
           },
           'pools_5d': {
               'leader': net.get('pool_leader_5d'),
               'top3_share': net.get('pool_top3_share_5d'),
               'hhi_known': net.get('pool_hhi_known_5d'),
           },
           'assets': {}}
    for sym in ('XMR', 'QUBIC'):
        closes = load_closes(sym)
        if len(closes) < 40:
            ctx['assets'][sym] = {'error': f'thin history ({len(closes)} closes)'}
            continue
        arets = log_returns(closes)
        b30 = rolling_beta(arets, btc_rets, 30)
        b90 = rolling_beta(arets, btc_rets, 90)
        # 30d window summary: asset move vs BTC-explained move.
        hook = None
        if len(b30) >= 30:
            w = b30[-30:]
            tot = sum(p['asset_ret'] for p in w)
            exp = sum((p['asset_ret'] - (p['residual'] or 0)) for p in w)
            hook = (f"{sym} {tot:+.1%} over 30d, "
                    f"{exp:+.1%} explained by BTC "
                    f"({(abs(exp) / abs(tot) * 100) if tot else 0:.0f}% of the move)")
        ctx['assets'][sym] = {
            'closes': len(closes),
            'beta_30d': b30[-1]['beta'] if b30 else None,
            'beta_90d': b90[-1]['beta'] if b90 else None,
            'residual_30d': round(sum(p['residual'] or 0 for p in b30[-30:]), 4) if len(b30) >= 30 else None,
            'hook': hook,
            'beta_series_30d': b30[-90:],
            'method': 'log returns, rolling covariance/variance, 30d/90d windows',
        }
        print(f"  [{sym}] beta30={ctx['assets'][sym]['beta_30d']} | {hook}")
    out = os.path.join(BASE_DIR, 'warehouse', 'btc_context.json')
    with open(out, 'w') as f:
        json.dump(ctx, f, indent=2, default=str)
    print(f"[BTC CONTEXT] saved to {out}")
    return ctx


if __name__ == '__main__':
    main()
