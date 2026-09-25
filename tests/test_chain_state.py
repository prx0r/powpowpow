import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "collectors"))

from collectors import chain_state


def canned_fetch(mapping):
    def fetch(url, **kwargs):
        assert kwargs.get("return_result") is True
        return mapping[url]

    return fetch


def test_poll_fetch_preserves_raw_observation_id(monkeypatch):
    monkeypatch.setattr(
        chain_state,
        "fetch_json",
        lambda url, **kwargs: {"parsed": {"ok": True}, "observation_id": "obs-1"},
    )
    parsed, observation_id = chain_state.poll_fetch(
        "https://example.invalid", source_id="test", chain_id="test"
    )
    assert parsed == {"ok": True}
    assert observation_id == "obs-1"


def test_poll_qubic_rows_carry_raw_event_ids(monkeypatch):
    rows = []
    monkeypatch.setattr(chain_state, "require_disk", lambda: True)
    monkeypatch.setattr(
        chain_state,
        "fetch_json",
        canned_fetch(
            {
                "https://rpc.qubic.org/v1/tick-info": {
                    "parsed": {"tickInfo": {"tick": 1, "epoch": 232}},
                    "observation_id": "tick-obs",
                },
                "https://rpc.qubic.org/v1/status": {
                    "parsed": {"lastProcessedTick": {"tickNumber": 1, "epoch": 232}},
                    "observation_id": "status-obs",
                },
                "https://analytics.qubic.li/api/stats": {
                    "parsed": {"latestTick": 1, "currentEpoch": 232},
                    "observation_id": "demand-obs",
                },
            }
        ),
    )
    monkeypatch.setattr(
        chain_state,
        "store_normalized",
        lambda table, chain, data, raw_event_id=None: rows.append(
            (table, chain, raw_event_id)
        ),
    )

    assert chain_state.poll_qubic({}) == 3
    assert ("chain_snapshot", "qubic", "tick-obs") in rows
    assert ("chain_snapshot", "qubic", "status-obs") in rows
    assert ("network_demand", "qubic", "demand-obs") in rows


def test_run_pass_only_selection_skips_other_chains(monkeypatch):
    called = []
    monkeypatch.setattr(chain_state, "save_netstate", lambda ns: None)
    for name in (
        "poll_qubic",
        "poll_xmr",
        "poll_kas",
        "poll_akt",
        "poll_nock",
        "poll_btc",
    ):
        monkeypatch.setattr(
            chain_state, name, lambda ns, name=name: called.append(name) or 1
        )

    stats = chain_state.run_pass({}, ["xmr", "btc"])

    assert called == ["poll_xmr", "poll_btc"]
    assert set(stats) == {"xmr", "btc"}


def test_low_disk_blocks_mining_writes(monkeypatch):
    monkeypatch.setattr(chain_state, "require_disk", lambda: False)
    monkeypatch.setattr(
        chain_state,
        "store_normalized",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not write")),
    )
    assert chain_state.poll_xmr({}) == "ERR low disk"
