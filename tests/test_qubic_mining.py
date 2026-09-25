import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import qubic_computors
import qubic_epoch


def test_qubic_epoch_preserves_both_rpc_observations(tmp_path, monkeypatch):
    rows = []
    monkeypatch.setattr(
        qubic_epoch,
        "fetch_json",
        lambda url, **kwargs: {
            "https://rpc.qubic.org/v1/tick-info": {
                "parsed": {"tickInfo": {"tick": 101, "epoch": 232, "initialTick": 1}},
                "observation_id": "tick-obs",
            },
            "https://rpc.qubic.org/v1/status": {
                "parsed": {"lastProcessedTicksPerEpoch": {"231": 100}},
                "observation_id": "status-obs",
            },
        }[url],
    )
    monkeypatch.setattr(
        qubic_epoch,
        "store_normalized",
        lambda table, chain, data, raw_event_id=None: rows.append(
            (table, chain, data, raw_event_id)
        ),
    )
    monkeypatch.setattr(qubic_epoch, "EPOCH_STATE_FILE", str(tmp_path / "epoch.json"))
    monkeypatch.setattr(qubic_epoch, "NETSTATE_FILE", str(tmp_path / "net.json"))

    qubic_epoch.main()

    assert rows
    table, chain, data, raw_event_id = rows[0]
    assert (table, chain, raw_event_id) == ("qubic_epoch", "qubic", "tick-obs")
    assert data["raw_status_id"] == "status-obs"


def test_qubic_computors_preserves_query_and_doge_observations(tmp_path, monkeypatch):
    rows = []
    monkeypatch.setattr(
        qubic_computors,
        "fetch_json",
        lambda url, **kwargs: {
            "https://rpc.qubic.org/v1/tick-info": {
                "parsed": {"tickInfo": {"epoch": 232}},
                "observation_id": "tick-obs",
            },
            "https://doge-stats.qubic.org/dispatcher.json": {
                "parsed": {"active_tasks": 9, "computor_shares": {"a": 1.0}},
                "observation_id": "doge-obs",
            },
        }[url],
    )

    class DummyResponse:
        def read(self):
            return json.dumps({"computorsLists": [{"identities": ["a"]}]}).encode()

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=20: DummyResponse()
    )
    monkeypatch.setattr(
        "core._archive_raw", lambda **kwargs: {"observation_id": "query-obs"}
    )
    monkeypatch.setattr(
        qubic_computors,
        "store_normalized",
        lambda table, chain, data, raw_event_id=None: rows.append(
            (table, chain, raw_event_id)
        ),
    )
    monkeypatch.setattr(
        qubic_computors, "load_prev_identities", lambda epoch: (set(), None)
    )
    monkeypatch.setattr(qubic_computors, "NETSTATE_FILE", str(tmp_path / "net.json"))

    qubic_computors.main()

    assert ("computor_snapshot", "qubic", "query-obs") in rows
    assert ("external_mining", "qubic", "doge-obs") in rows
