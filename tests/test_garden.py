"""Garden integrity tests — the review's required invariants, cheap form.

Covers: raw round-trip (incl. >256KB compression path), lineage
resolution, UTC-only timestamps, L2 gap detection, point-in-time
dating, missing-data refusal, observation determinism.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'RAW_DIR', str(tmp_path / 'raw'))
    monkeypatch.setattr(core, 'BASE_DIR', str(tmp_path))
    # core/ package shadows core.py, so patching the package namespace does not
    # reach store_normalized / _archive_raw. Patch their own globals or tests
    # write observations into the live warehouse.
    for fn in (core.store_normalized, core._archive_raw):
        monkeypatch.setitem(fn.__globals__, 'RAW_DIR', str(tmp_path / 'raw'))
        monkeypatch.setitem(fn.__globals__, 'BASE_DIR', str(tmp_path))
    os.makedirs(str(tmp_path / 'raw'), exist_ok=True)
    return tmp_path


def test_raw_round_trip(isolated):
    body = '{"tick":80792768,"epoch":231}'
    obs = core._archive_raw(
        chain_id='qubic', source_id='qubic-rpc', endpoint='https://x',
        event_time=None, observed_at=core.utcnow(),
        response_received=core.utcnow(), http_status=200,
        raw_body=body, parsed_payload={'tick': 80792768})
    stored = json.load(open(obs['filepath']))
    assert stored['raw_payload'] == body
    assert stored['raw_encoding'] == 'utf-8'
    assert stored['payload_hash'] == core.canonical_hash(body)
    import hashlib
    canonical = json.dumps(body, sort_keys=True, separators=(',', ':'),
                           default=str)
    assert stored['payload_hash'] == hashlib.sha256(canonical.encode()).hexdigest()


def test_raw_large_body_lossless(isolated):
    import zlib
    import base64
    body = '{"data":"' + 'x' * 300000 + '"}'
    obs = core._archive_raw(
        chain_id='venue', source_id='t', endpoint='https://x',
        event_time=None, observed_at=core.utcnow(),
        response_received=core.utcnow(), http_status=200,
        raw_body=body, parsed_payload=None)
    stored = json.load(open(obs['filepath']))
    assert stored['raw_encoding'] == 'zlib-base64'
    recovered = zlib.decompress(base64.b64decode(stored['raw_payload'])).decode()
    assert recovered == body
    assert stored['payload_hash'] == core.canonical_hash(body)


def test_observation_deterministic(isolated):
    kw = dict(chain_id='xmr', source_id='s', endpoint='https://x',
              event_time=None, observed_at='2026-09-19T00:00:00Z',
              response_received='2026-09-19T00:00:01Z', http_status=200,
              raw_body='{"a":1}', parsed_payload={'a': 1})
    a = core._archive_raw(**kw)
    b = core._archive_raw(**kw)
    assert a['observation_id'] == b['observation_id']


def test_lineage_resolves(isolated):
    obs = core._archive_raw(
        chain_id='venue', source_id='s', endpoint='https://x',
        event_time=None, observed_at=core.utcnow(),
        response_received=core.utcnow(), http_status=200,
        raw_body='{}', parsed_payload={})
    core.store_normalized('trade', 'venue', {'symbol': 'X'},
                          raw_event_id=obs['observation_id'])
    rows = []
    import glob
    for f in glob.glob(os.path.join(
            str(isolated), 'warehouse', 'normalized', 'trade',
            'chain=venue', 'date=*', 'hour=*.jsonl')):
        rows += [json.loads(l) for l in open(f)]
    assert rows and rows[0]['raw_event_id'] == obs['observation_id']
    assert os.path.exists(os.path.join(str(isolated), 'raw', 'venue',
                                       obs['observation_id'] + '.json'))


def test_timestamps_utc():
    assert core.utcnow().endswith('Z')
    assert core.parse_event_time(1789820106).endswith('+00:00')
    # row_date prefers exchange time over receive time (point-in-time)
    assert core.row_date({'exchange_time': '2026-07-01T00:00:01+00:00',
                          'receive_time': '2026-09-19T00:00:00Z'}) == '2026-07-01'


def test_l2_gap_detection():
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'collectors'))
    import importlib
    l2 = importlib.import_module('l2_archival')
    g = l2.StreamGap()
    assert g.check('s', 10) == 'first'
    assert g.check('s', 11) == 'ok'
    assert g.check('s', 11) == 'duplicate'
    assert g.check('s', 14) == 'gap'
    assert g.check('s', None) == 'unknown'


def test_safetrade_discovery_stays_bounded(monkeypatch):
    import importlib
    l2 = importlib.import_module('l2_archival')
    markets = [{'id': market} for market in l2.SEED_MARKETS]
    markets.extend([{'id': 'btcusdt'}, {'id': 'extrausdt'}])
    monkeypatch.setattr(l2, 'fetch_json', lambda *args, **kwargs: markets)
    assert l2.discover_seed_markets() == l2.SEED_MARKETS


def test_safetrade_websocket_lineage(monkeypatch):
    import importlib
    l2 = importlib.import_module('l2_archival')
    captured = {}

    def archive(**kwargs):
        captured.update(kwargs)
        return {'observation_id': 'ws-observation'}

    monkeypatch.setattr(l2, '_archive_raw', archive)
    entry = {
        'stream': 'btcusdt.trades',
        'payload': [{'id': 1}],
        'event_time': '2026-09-25T13:00:00Z',
        'seq': 7,
    }
    collector = l2.L2Archival()
    assert collector.archive_raw(entry, '2026-09-25T13:00:01Z', 'trades') == 'ws-observation'
    assert captured['transport'] == 'websocket'
    assert captured['source_role'] == 'raw_venue'
    assert captured['event_type'] == 'btcusdt.trades'


def test_safetrade_rest_checkpoint_lineage(monkeypatch):
    import asyncio
    import importlib
    l2 = importlib.import_module('l2_archival')
    rows = []

    def fetch(*args, **kwargs):
        return {
            'parsed': {'bids': [['1', '2']], 'asks': [['2', '2']]},
            'observation_id': 'rest-observation',
        }

    monkeypatch.setattr(l2, 'fetch_json', fetch)
    monkeypatch.setattr(
        l2,
        'store_normalized',
        lambda table, chain, data: rows.append(data),
    )
    asyncio.run(l2.L2Archival().rest_checkpoint(['btcusdt']))
    assert rows[0]['raw_event_id'] == 'rest-observation'


def test_signals_refuse_thin_data(isolated, monkeypatch):
    import signals
    monkeypatch.setattr(signals, 'BASE_DIR', str(isolated))
    assert signals.build_signals('2026-01-01') == []
    assert signals.build_flow_signals('2026-01-01') == []
    assert signals.build_required_signals('2026-01-01') == []


def test_cowriters_survive_pass(isolated, monkeypatch):
    """Regression: a pass must only persist the keys it changed.

    Four writers share chains/network_state.json. Replacing the whole file
    after seconds of polling reverted keys a co-writer had added meanwhile.
    """
    import copy as _copy

    import collectors.chain_state as cs

    path = str(isolated / "network_state.json")
    monkeypatch.setattr(cs, "NETSTATE_FILE", path)
    core.atomic_json_write(path, {
        "QUBIC": {"epoch": 232, "burn_rate": 0.775, "computors": 676},
        "XMR": {"height": 100},
    })

    ns = cs.load_netstate()
    co_writer = _copy.deepcopy(ns)
    co_writer["QUBIC"]["active_addresses"] = 671275
    core.save_state_delta(path, core.dict_delta(ns, co_writer))

    snapshot = _copy.deepcopy(ns)
    ns.setdefault("XMR", {})["height"] = 123
    cs.save_netstate(ns, snapshot)

    after = json.load(open(path))
    assert after["QUBIC"]["burn_rate"] == 0.775
    assert after["QUBIC"]["computors"] == 676
    assert after["QUBIC"]["active_addresses"] == 671275
    assert after["XMR"]["height"] == 123
