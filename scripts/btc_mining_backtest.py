"""
BTC mining backtest — do mining features explain forward returns?

First empirical test the garden can run honestly: 355 days of BTC
chain history (hashrate, difficulty, revenue, fees) + 366 closes.
Features vs 7d/30d forward log returns: correlation + quintile spread.

In-sample, descriptive, no trading recommendation. This is the M1
incremental-value seed: if mining features don't beat M0 (BTC momentum
alone), the garden knows before building on it.

Usage:
    python3 scripts/btc_mining_backtest.py
"""

import glob
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def hashprice_ph_day(revenue_usd_day, network_hashrate_ghs):
    if not revenue_usd_day or not network_hashrate_ghs:
        return None
    if network_hashrate_ghs <= 0:
        return None
    return revenue_usd_day / (network_hashrate_ghs / 1e6)


def load_btc_daily():
    """One row per date: closes + chain features joined."""
    closes = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'price_history',
            'chain=btc', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('close_usd') and r.get('date'):
                    closes[r['date']] = float(r['close_usd'])
    feats = {}
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'chain_snapshot',
            'chain=btc', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                d = (r.get('event_time') or '')[:10]
                if not d:
                    continue
                a = feats.setdefault(d, {})
                for k in ('network_hashrate_ghs', 'network_hashrate_ths', 'difficulty',
                          'miners_revenue_usd', 'fees_usd_day'):
                    if r.get(k) is not None:
                        a[k] = r[k]
        dates = sorted(set(closes) & set(feats))
    rows = []
    for d in dates:
        r = {'date': d, 'close': closes[d], **feats[d]}
        hashrate_ghs = hashrate_ghs(r)
        r['hashprice_ph_day'] = hashprice_ph_day(
            r.get('miners_revenue_usd'), hashrate_ghs)
        if r.get('fees_usd_day') and r.get('miners_revenue_usd'):
            r['fee_share'] = r['fees_usd_day'] / r['miners_revenue_usd']
        rows.append(r)
    return rows


def hashrate_ghs(row):
    if row.get('network_hashrate_ghs'):
        return row['network_hashrate_ghs']
    ths = row.get('network_hashrate_ths')
    return ths * 1000 if ths else None


def pct(series, lag):
    out = []
    for i in range(lag, len(series)):
        a, b = series[i - lag], series[i]
        out.append((b['date'], (b['v'] - a['v']) / a['v'] if a['v'] else None))
    return out


def fwd_rets(closes, horizon):
    out = []
    for i in range(len(closes) - horizon):
        a, b = closes[i], closes[i + horizon]
        out.append((b[0], math.log(b[1] / a[1])))
    return out


def corr(xs, ys):
    n = len(xs)
    if n < 20:
        return None, n
    mx, my = sum(xs) / n, sum(ys) / n
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else None, n


def quintile_spread(feat, fwd):
    """Mean forward ret top-quintile minus bottom-quintile by feature."""
    fm = dict(feat)
    pairs = [(fm[d], r) for d, r in fwd if d in fm and fm[d] is not None]
    if len(pairs) < 50:
        return None, len(pairs)
    pairs.sort()
    q = len(pairs) // 5
    lo = sum(r for _, r in pairs[:q]) / q
    hi = sum(r for _, r in pairs[-q:]) / q
    return hi - lo, len(pairs)


def main():
    rows = load_btc_daily()
    print(f"[BTC MINING BACKTEST] {len(rows)} joint days")
    closes = [(r['date'], r['close']) for r in rows]
    results = []
    feature_defs = [
        ('hashprice_ph_day', None),
        ('fee_share', None),
        ('difficulty_wow', ('difficulty', 7)),
        ('hashrate_wow', ('hashrate_ghs', 7)),
        ('revenue_wow', ('miners_revenue_usd', 7)),
    ]
    feats = {}
    for name, spec in feature_defs:
        if spec is None:
            feats[name] = [(r['date'], r.get(name)) for r in rows]
        else:
            key, lag = spec
            if key == 'hashrate_ghs':
                s = [{'date': r['date'], 'v': hashrate_ghs(r)}
                     for r in rows if hashrate_ghs(r)]
            else:
                s = [{'date': r['date'], 'v': r[key]} for r in rows if r.get(key)]
            feats[name] = [(d, v) for d, v in pct(s, lag)]
    for horizon in (7, 30):
        fwd = fwd_rets(closes, horizon)
        print(f"--- forward {horizon}d (n={len(fwd)}) ---")
        for name in [f[0] for f in feature_defs]:
            fm = dict(feats[name])
            paired = [(fm[d], r) for d, r in fwd if d in fm and fm[d] is not None]
            if len(paired) >= 20:
                xs = [p[0] for p in paired]
                ys = [p[1] for p in paired]
                c, n = corr(xs, ys)
            else:
                c, n = None, len(paired)
            qs, qn = quintile_spread(feats[name], fwd)
            qstr = f"{qs:+.3f}" if qs is not None else "n/a"
            print(f"  {name:18} corr={c if c is None else round(c,3)!s:>7} (n={n:3})  Q5-Q1={qstr} (n={qn})")
            results.append({'feature': name, 'horizon': horizon,
                            'corr': c, 'n': n, 'qspread': qs, 'qn': qn})
    out = os.path.join(BASE_DIR, 'warehouse', 'btc_mining_backtest.json')
    with open(out, 'w') as f:
        json.dump({'results': results, 'days': len(rows)}, f, indent=2, default=str)
    print(f"[SAVED] {out}")


if __name__ == '__main__':
    main()
