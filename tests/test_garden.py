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


def test_signals_refuse_thin_data(isolated, monkeypatch):
    import signals
    monkeypatch.setattr(signals, 'BASE_DIR', str(isolated))
    assert signals.build_signals('2026-01-01') == []
    assert signals.build_flow_signals('2026-01-01') == []
    assert signals.build_required_signals('2026-01-01') == []
