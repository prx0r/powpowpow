"""
Chain-state poller — live network truth for reachable chains.

QUBIC (first-party RPC, canonical) • XMR (localmonero, derived) •
KAS (api.kaspa.org, canonical-ish) • NOCK (nockscan, derived).
Every response auto-archived raw via core.fetch_json. Normalized
chain_snapshot rows + chains/network_state.json (live overrides for
money math + signals: hashrate, emission, supply, price hints).

PRL is queued, not dry-diligent: PearlTrack /api/v1/* 404s from here,
pearld RPC times out, explorer SPAs expose no API. Needs own pearld
node (separate task: binary + sync).

Usage:
    python3 collectors/chain_state.py --once
    python3 collectors/chain_state.py --cadence 300
"""

import argparse
import json
import os
import signal
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

NETSTATE_FILE = os.path.join(BASE_DIR, 'chains', 'network_state.json')
PID_FILE = os.path.join(BASE_DIR, 'warehouse', 'chain_state.pid')
HEARTBEAT_FILE = os.path.join(BASE_DIR, 'warehouse', 'chain_state_heartbeat.json')

RUNNING = True


def load_netstate():
    try:
        return json.load(open(NETSTATE_FILE))
    except OSError:
        return {}


def save_netstate(ns):
    tmp = NETSTATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(ns, f, indent=2, default=str)
    os.replace(tmp, NETSTATE_FILE)


def poll_qubic(ns):
    ok = 0
    tick = fetch_json('https://rpc.qubic.org/v1/tick-info',
                      source_id='qubic-rpc', chain_id='qubic')
    if tick and isinstance(tick, dict):
        ti = tick.get('tickInfo', tick)
        store_normalized('chain_snapshot', 'qubic', {
            'height': ti.get('tick'), 'epoch': ti.get('epoch'),
            'source_role': 'canonical', 'source_id': 'qubic-rpc'})
        ns.setdefault('QUBIC', {}).update({
            'epoch': ti.get('epoch'), 'tick': ti.get('tick'),
            'tick_source': 'rpc.qubic.org/v1/tick-info', 'as_of': utcnow()})
        ok += 1
    status = fetch_json('https://rpc.qubic.org/v1/status',
                        source_id='qubic-rpc', chain_id='qubic')
    if status and isinstance(status, dict):
        lp = status.get('lastProcessedTick', {}) or {}
        store_normalized('chain_snapshot', 'qubic', {
            'height': lp.get('tickNumber'), 'epoch': lp.get('epoch'),
            'peers': status.get('numberOfConnectedPeers'),
            'source_role': 'canonical', 'source_id': 'qubic-rpc'})
        ok += 1
    # analytics.qubic.li: network demand totals (deltas = demand growth)
    qli = fetch_json('https://analytics.qubic.li/api/stats',
                     source_id='qubic-analytics', chain_id='qubic')
    if qli and isinstance(qli, dict):
        store_normalized('network_demand', 'qubic', {
            'tick': qli.get('latestTick'), 'epoch': qli.get('currentEpoch'),
            'total_transactions': qli.get('totalTransactions'),
            'total_transfers': qli.get('totalTransfers'),
            'total_volume': qli.get('totalVolume'),
            'source_role': 'derived', 'source_id': 'qubic-analytics'})
        ns.setdefault('QUBIC', {}).update({
            'demand_tick': qli.get('latestTick'),
            'demand_epoch': qli.get('currentEpoch'),
            'total_transactions': qli.get('totalTransactions'),
            'total_transfers': qli.get('totalTransfers'),
            'total_volume': qli.get('totalVolume'),
            'demand_source': 'analytics.qubic.li (day deltas = demand growth)',
            'as_of': utcnow()})
        ok += 1
    return ok


def poll_xmr(ns):
    data = fetch_json('https://localmonero.co/blocks/api/get_stats',
                      source_id='localmonero', chain_id='xmr')
    if not data or not isinstance(data, dict):
        return 0
    try:
        total_em = int(data.get('total_emission', 0)) / 1e12
    except (TypeError, ValueError):
        total_em = None
    store_normalized('chain_snapshot', 'xmr', {
        'height': data.get('height'), 'difficulty': data.get('difficulty'),
        'hashrate': data.get('hashrate'),
        'hashrate_unit': 'H/s (as reported)',
        'total_emission': total_em,
        'last_reward': (lambda v: int(v) / 1e12 if v else None)(data.get('last_reward')),
        'source_role': 'derived', 'source_id': 'localmonero'})
    e = ns.setdefault('XMR', {})
    e.update({'network_hashrate': data.get('hashrate'),
              'hashrate_source': 'localmonero 1 poll (H/s as reported)',
              'height': data.get('height'), 'difficulty': data.get('difficulty'),
              'as_of': utcnow()})
    # xmrchain.net: fee market + mempool pressure + canonical difficulty
    net = fetch_json('https://xmrchain.net/api/networkinfo',
                     source_id='xmrchain', chain_id='xmr')
    if net and isinstance(net.get('data'), dict):
        nd = net['data']
        e['fee_per_kb'] = nd.get('fee_per_kb')
        e['fee_estimate'] = nd.get('fee_estimate')
        e['block_size_median'] = nd.get('block_size_median')
        e['hf_version'] = nd.get('current_hf_version')
        e['fee_source'] = 'xmrchain.net/api/networkinfo'
        store_normalized('fee_market', 'xmr', {
            'fee_per_kb': nd.get('fee_per_kb'),
            'fee_estimate': nd.get('fee_estimate'),
            'block_size_median': nd.get('block_size_median'),
            'difficulty': nd.get('difficulty'),
            'source_role': 'derived', 'source_id': 'xmrchain'})
    pool = fetch_json('https://xmrchain.net/api/mempool?limit=1',
                      source_id='xmrchain', chain_id='xmr')
    if pool and isinstance(pool.get('data'), dict):
        txs = pool['data'].get('txs', [])
        e['mempool_txs_sampled'] = len(txs)
        store_normalized('mempool_snapshot', 'xmr', {
            'txs_in_page': len(txs),
            'source_role': 'derived', 'source_id': 'xmrchain'})
    # p2pool: decentralized supply-response telemetry (miners + hashrate)
    p2p = fetch_json('https://p2pool.observer/api/pool/stats',
                     source_id='p2pool-observer', chain_id='xmr')
    if p2p and isinstance(p2p.get('pool_statistics'), dict):
        ps = p2p['pool_statistics']
        e['p2pool_hashrate'] = ps.get('hashRate')
        e['p2pool_miners'] = ps.get('miners')
        e['p2pool_last_block'] = ps.get('lastBlockFound')
        e['p2pool_source'] = 'p2pool.observer (decentralized mining share)'
        store_normalized('pool_snapshot', 'xmr', {
            'pool': 'p2pool', 'hashrate': ps.get('hashRate'),
            'miners': ps.get('miners'),
            'last_block': ps.get('lastBlockFound'),
            'total_blocks': ps.get('totalBlocksFound'),
            'source_role': 'derived', 'source_id': 'p2pool-observer'})
    return 1


def poll_kas(ns):
    ok = 0
    hr = fetch_json('https://api.kaspa.org/info/hashrate',
                    source_id='kaspa-api', chain_id='kas')
    price = fetch_json('https://api.kaspa.org/info/price',
                       source_id='kaspa-api', chain_id='kas')
    supply = fetch_json('https://api.kaspa.org/info/coinsupply/circulating',
                        source_id='kaspa-api', chain_id='kas')
    hrv = hr.get('hashrate') if isinstance(hr, dict) else None
    prv = price.get('price') if isinstance(price, dict) else None
    store_normalized('chain_snapshot', 'kas', {
        'network_hashrate_raw': hrv,
        'hashrate_unit': 'UNCONFIRMED (api.kaspa.org/info/hashrate as-is)',
        'price_usd': prv, 'circulating_supply': supply,
        'source_role': 'canonical-ish', 'source_id': 'kaspa-api'})
    e = ns.setdefault('KAS', {})
    e.update({'network_hashrate_raw': hrv,
              'hashrate_unit': 'UNCONFIRMED',
              'price_usd': prv, 'circulating_supply': supply,
              'supply_source': 'api.kaspa.org (for day-over-day emission delta)',
              'as_of': utcnow()})
    # Supply-delta emission rate: needs two supply points separated in
    # time. Rate = delta/dt annualized to per-day. Requires dt > 1h.
    now_ts = time.time()
    prev = e.get('prev_supply')
    prev_ts = e.get('prev_supply_ts')
    if prev and prev_ts and supply:
        try:
            dt = now_ts - float(prev_ts)
            if dt > 3600:
                rate = (float(supply) - float(prev)) / dt * 86400
                if rate > 0:
                    e['daily_emission_delta'] = round(rate, 2)
                    e['emission_source'] = (
                        'circulating-supply delta rate (measured, '
                        f'{dt/3600:.1f}h window)')
                    ok += 1
        except (TypeError, ValueError):
            pass
    if not e.get('prev_supply_ts') or not prev:
        e['prev_supply'] = supply
        e['prev_supply_ts'] = now_ts
    # else: keep widening the window; rate accuracy grows with dt.
    return ok + (1 if hrv else 0)


def poll_akt(ns):
    """AKT: circulating supply sampling (Cosmos dynamic inflation has no
    clean schedule — emission comes from supply-delta rate like KAS)."""
    sup = fetch_json('https://supply.akash.pub/circulating',
                     source_id='akash-supply', chain_id='akt')
    try:
        supply = float(sup) if not isinstance(sup, dict) else None
    except (TypeError, ValueError):
        supply = None
    if supply is None:
        return 0
    store_normalized('chain_snapshot', 'akt', {
        'circulating_supply': supply,
        'source_role': 'canonical-ish', 'source_id': 'akash-supply'})
    e = ns.setdefault('AKT', {})
    now_ts = time.time()
    prev, prev_ts = e.get('prev_supply'), e.get('prev_supply_ts')
    ok = 0
    if prev and prev_ts:
        try:
            dt = now_ts - float(prev_ts)
            if dt > 3600:
                rate = (supply - float(prev)) / dt * 86400
                if rate > 0:
                    e['daily_emission_delta'] = round(rate, 2)
                    e['emission_source'] = ('akash supply-delta rate '
                                            f'(measured, {dt/3600:.1f}h window)')
                    ok = 1
        except (TypeError, ValueError):
            pass
    if not e.get('prev_supply_ts') or not prev:
        e['prev_supply'] = supply
        e['prev_supply_ts'] = now_ts
    e.update({'circulating_supply': supply, 'as_of': utcnow(),
              'supply_source': 'supply.akash.pub/circulating'})
    return ok + 1


def poll_nock(ns):
    ok = 0
    blocks = fetch_json('https://nockscan.net/api/v1/recent-blocks',
                        source_id='nockscan', chain_id='nock')
    bl = (blocks.get('blocks') if isinstance(blocks, dict) else blocks) or []
    if bl:
        b0 = bl[0] if isinstance(bl, list) else {}
        store_normalized('chain_snapshot', 'nock', {
            'height': b0.get('height'), 'tip_hash': b0.get('hash'),
            'block_time': b0.get('timestamp'),
            'source_role': 'derived', 'source_id': 'nockscan'})
        ns.setdefault('NOCK', {}).update({
            'height': b0.get('height'), 'as_of': utcnow(),
            'blocks_source': 'nockscan recent-blocks'})
        ok += 1
    pr = fetch_json('https://nockscan.net/api/v1/proof-rate',
                    source_id='nockscan', chain_id='nock')
    if pr:
        store_normalized('proof_rate', 'nock', {
            'payload': pr, 'source_role': 'derived',
            'source_id': 'nockscan'})
        ok += 1
    return ok


def run_pass(ns):
    """One pass over all chains. Callers must pass a FRESHLY LOADED ns
    each time (never a long-lived in-memory copy) — other writers
    (epoch engine, computors) update the same file, and saving a stale
    copy would silently delete their keys (lost-update bug, found
    2026-09-19). Runtime-only baselines (prev_supply) live in RUNTIME
    and are merged in here."""
    for sym, base in RUNTIME.items():
        ns.setdefault(sym, {}).update(base)
    stats = {}
    for name, fn in (('qubic', poll_qubic), ('xmr', poll_xmr),
                     ('kas', poll_kas), ('akt', poll_akt), ('nock', poll_nock)):
        try:
            stats[name] = fn(ns)
        except Exception as e:
            stats[name] = f'ERR {str(e)[:100]}'
        time.sleep(1)
    for sym in ('KAS', 'AKT'):
        e = ns.get(sym, {})
        if e.get('prev_supply') is not None:
            RUNTIME[sym] = {'prev_supply': e['prev_supply'],
                            'prev_supply_ts': e.get('prev_supply_ts')}
    save_netstate(ns)
    return stats


# Runtime-only baselines, never persisted directly (merged per pass).
RUNTIME = {}


def main():
    global RUNNING
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--cadence', type=int, default=300)
    args = ap.parse_args()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: globals().update(RUNNING=False))

    ns = load_netstate()
    if args.once:
        print(run_pass(ns))
        return
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(f"[CHAIN_STATE] loop cadence={args.cadence}s pid={os.getpid()}")
    try:
        while RUNNING:
            stats = run_pass(load_netstate())  # fresh each pass: never
            # overwrite co-writers (epoch engine, computors)
            with open(HEARTBEAT_FILE, 'w') as f:
                json.dump({'heartbeat_at': utcnow(), 'mode': 'daemon',
                           'stats': stats}, f, indent=2, default=str)
            print(f"[PASS] {stats}")
            for _ in range(args.cadence):
                if not RUNNING:
                    break
                time.sleep(1)
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


if __name__ == '__main__':
    main()
