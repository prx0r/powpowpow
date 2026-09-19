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
    # Supply-delta emission: needs yesterday's supply; compute when present.
    prev = e.get('prev_supply')
    if prev and supply:
        try:
            e['daily_emission_delta'] = float(supply) - float(prev)
            e['emission_source'] = 'circulating-supply day delta (measured)'
            ok += 1
        except (TypeError, ValueError):
            pass
    e['prev_supply'] = supply
    return ok + (1 if hrv else 0)


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
    stats = {}
    for name, fn in (('qubic', poll_qubic), ('xmr', poll_xmr),
                     ('kas', poll_kas), ('nock', poll_nock)):
        try:
            stats[name] = fn(ns)
        except Exception as e:
            stats[name] = f'ERR {str(e)[:100]}'
        time.sleep(1)
    save_netstate(ns)
    return stats


def main():
    global RUNNING
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--cadence', type=int, default=300)
    args = ap.parse_args()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: globals().update(RUNNING=False))

    ns = load_state = load_netstate()
    if args.once:
        print(run_pass(ns))
        return
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(f"[CHAIN_STATE] loop cadence={args.cadence}s pid={os.getpid()}")
    try:
        while RUNNING:
            stats = run_pass(ns)
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
