"""
Qubic computor + external-mining telemetry.

- Archive Query API getComputorListsForEpoch: identities per epoch.
  Stores computor_snapshot rows + churn vs previous epoch snapshot
  (retained/new/dropped, count) → supplier concentration observable.
- doge-stats dispatcher.json: active_tasks + computor_shares → the
  external DOGE-mining revenue leg (buyback/burn funding source).

Hourly cadence is plenty (computor sets change per epoch). Also
refreshes chains/network_state.json QUBIC computor fields.

Sources: rpc.qubic.org/query/v1 (official archive API),
doge-stats.qubic.org/dispatcher.json.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

NETSTATE_FILE = os.path.join(BASE_DIR, 'chains', 'network_state.json')


def load_prev_identities(epoch):
    """Latest stored identities for comparison (any older epoch)."""
    import glob
    best = None
    for f in glob.glob(os.path.join(
            BASE_DIR, 'warehouse', 'normalized', 'computor_snapshot',
            'chain=qubic', 'date=*', 'hour=*.jsonl')):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('epoch', 0) < (epoch or 10**9) and \
                        (best is None or r.get('epoch', 0) > best.get('epoch', 0)):
                    best = r
    return set(best.get('identities', [])) if best else set(), \
        (best or {}).get('epoch')


def main():
    tick = fetch_json('https://rpc.qubic.org/v1/tick-info',
                      source_id='qubic-rpc', chain_id='qubic')
    epoch = ((tick or {}).get('tickInfo', tick or {})).get('epoch')
    if not epoch:
        print("[COMPUTORS] no epoch from tick-info")
        return

    data = None
    # NOTE: archive endpoint is POST-only and core.fetch_json is
    # GET-only, so POST directly here (raw archived below — moat rule
    # applies to POST too).
    import urllib.request
    req = urllib.request.Request(
        'https://rpc.qubic.org/query/v1/getComputorListsForEpoch',
        data=json.dumps({'epoch': epoch}).encode(),
        headers={'Content-Type': 'application/json',
                 'User-Agent': 'PowPowPow/1.0'})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        from core import _archive_raw
        _archive_raw(chain_id='qubic', source_id='qubic-query',
                     endpoint='POST getComputorListsForEpoch',
                     event_time=None, observed_at=utcnow(),
                     response_received=utcnow(), http_status=200,
                     raw_body=json.dumps(data, default=str),
                     parsed_payload={'epoch': epoch,
                                     'n_identities': sum(
                                         len(l.get('identities', []))
                                         for l in data.get('computorsLists', []))},
                     request_params={'epoch': epoch},
                     quality_flags=['post'])
    except Exception as e:
        print(f"[COMPUTORS] query API ERR {str(e)[:120]}")
        return

    identities = []
    for lst in (data.get('computorsLists') or []):
        identities += lst.get('identities', []) or []
    identities = sorted(set(identities))
    prev, prev_epoch = load_prev_identities(epoch)
    cur = set(identities)
    churn = {'epoch': epoch, 'count': len(cur),
             'retained': len(cur & prev) if prev else None,
             'new': len(cur - prev) if prev else None,
             'dropped': len(prev - cur) if prev else None,
             'vs_epoch': prev_epoch}
    store_normalized('computor_snapshot', 'qubic', {
        **churn, 'identities': identities,
        'source_role': 'canonical', 'source_id': 'qubic-query'})
    print(f"[COMPUTORS] epoch={epoch} n={len(cur)} "
          f"+{churn['new']}/-{churn['dropped']} vs {prev_epoch}")

    doge = fetch_json('https://doge-stats.qubic.org/dispatcher.json',
                      source_id='doge-stats', chain_id='qubic')
    if doge and isinstance(doge, dict):
        shares = doge.get('computor_shares', {}) or {}
        vals = [float(v) for v in shares.values()
                if isinstance(v, (int, float))]
        store_normalized('external_mining', 'qubic', {
            'epoch': epoch, 'active_tasks': doge.get('active_tasks'),
            'computors_sharing': len(vals),
            'share_mean': sum(vals) / len(vals) if vals else None,
            'share_max': max(vals) if vals else None,
            'source_role': 'derived', 'source_id': 'doge-stats'})
        print(f"[DOGE] tasks={doge.get('active_tasks')} sharers={len(vals)}")

    try:
        ns = json.load(open(NETSTATE_FILE))
    except (OSError, ValueError):
        ns = {}
    q = ns.setdefault('QUBIC', {})
    q.update({'computors': len(cur), 'computor_churn': churn,
              'doge_tasks': (doge or {}).get('active_tasks'),
              'as_of': utcnow()})
    with open(NETSTATE_FILE + '.tmp', 'w') as f:
        json.dump(ns, f, indent=2, default=str)
    os.replace(NETSTATE_FILE + '.tmp', NETSTATE_FILE)


if __name__ == '__main__':
    main()
