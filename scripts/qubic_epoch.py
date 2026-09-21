"""
Qubic epoch engine — validated inflation, not tick soup.

Reads rpc.qubic.org tick-info + status, derives epoch progress, tick
rate, and empirical ticks-per-epoch, then applies the documented
halving schedule to produce NET emission (gross is constant 1T/week;
burn share is what halves):

  epoch < 123 : burn   0% (pre-SWATCH)
  123 - 174   : burn  15%
  175 - 226   : burn  55%   (halving 1, Aug 2025)
  227+        : burn  78.75% (halving 2, Aug 19 2026)

Net/week = 1e12 * (1 - burn). Writes chains/network_state.json QUBIC
section (daily_emission, burn_rate, epoch, progress, tick_rate), which
money math + signals prefer over static seeds.

Sources: qubic.org/halving, qubic.org blog (41.5T burned, May 2026),
docs.qubic.org/learn/emission-mechanism.
"""

import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

NETSTATE_FILE = os.path.join(BASE_DIR, 'chains', 'network_state.json')
EPOCH_STATE_FILE = os.path.join(BASE_DIR, 'warehouse', 'qubic_epoch_state.json')
GROSS_PER_WEEK = 1e12


def burn_rate_for_epoch(epoch):
    if epoch is None:
        return None
    if epoch < 123:
        return 0.0
    if epoch < 175:
        return 0.15
    if epoch < 227:
        return 0.55
    return 0.7875


def load_prev():
    try:
        return json.load(open(EPOCH_STATE_FILE))
    except (OSError, ValueError):
        return {}


def save_prev(d):
    with open(EPOCH_STATE_FILE + '.tmp', 'w') as f:
        json.dump(d, f)
    os.replace(EPOCH_STATE_FILE + '.tmp', EPOCH_STATE_FILE)


def main():
    tick = fetch_json('https://rpc.qubic.org/v1/tick-info',
                      source_id='qubic-rpc', chain_id='qubic')
    status = fetch_json('https://rpc.qubic.org/v1/status',
                        source_id='qubic-rpc', chain_id='qubic')
    ti = (tick or {}).get('tickInfo', tick or {})
    epoch, cur, initial = ti.get('epoch'), ti.get('tick'), ti.get('initialTick')
    if not epoch or not cur:
        print("[QUBIC] tick-info unreachable, skipping (no Nones written)")
        return

    per_epoch = (status or {}).get('lastProcessedTicksPerEpoch', {}) or {}
    vals = sorted(per_epoch.values())
    # map values are per-epoch tick counts (13-15M range); median is robust
    ticks_per_epoch = sorted(vals)[len(vals) // 2] if vals else None

    progress = None
    if cur and initial and ticks_per_epoch:
        progress = round((cur - initial) / ticks_per_epoch, 4)

    prev = load_prev()
    now = time.time()
    tick_rate = None
    if prev.get('tick') and prev.get('ts') and cur and cur > prev['tick']:
        dt = now - prev['ts']
        if dt > 30:
            tick_rate = round((cur - prev['tick']) / dt, 2)
    save_prev({'tick': cur, 'ts': now})

    burn = burn_rate_for_epoch(epoch)
    net_week = GROSS_PER_WEEK * (1 - burn) if burn is not None else None
    net_day = net_week / 7 if net_week else None

    store_normalized('qubic_epoch', 'qubic', {
        'epoch': epoch, 'tick': cur, 'initial_tick': initial,
        'ticks_per_epoch_empirical': ticks_per_epoch,
        'epoch_progress': progress, 'tick_rate': tick_rate,
        'burn_rate': burn, 'net_emission_week': net_week,
        'net_emission_day': net_day,
        'source_role': 'canonical', 'source_id': 'qubic-rpc'})

    try:
        ns = json.load(open(NETSTATE_FILE))
    except (OSError, ValueError):
        ns = {}
    q = ns.setdefault('QUBIC', {})
    q.update({'epoch': epoch, 'tick': cur, 'epoch_progress': progress,
              'tick_rate': tick_rate, 'ticks_per_epoch': ticks_per_epoch,
              'burn_rate': burn, 'daily_emission': net_day,
              'emission_source': 'qubic epoch engine: 1T gross/week net of '
                                 f'{burn} burn (post-227 schedule)',
              'emission_confidence': 'medium',
              'gross_per_week': GROSS_PER_WEEK,
              'as_of': utcnow()})
    with open(NETSTATE_FILE + '.tmp', 'w') as f:
        json.dump(ns, f, indent=2, default=str)
    os.replace(NETSTATE_FILE + '.tmp', NETSTATE_FILE)

    print(f"[QUBIC] epoch={epoch} tick={cur} progress={progress} "
          f"rate={tick_rate}/s burn={burn} "
          f"net_day={round(net_day) if net_day else None:,}")


if __name__ == '__main__':
    main()
