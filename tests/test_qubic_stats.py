import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from collectors import qubic_stats


def test_unwrap_flattens_data_wrapper():
    assert qubic_stats.unwrap({"data": {"a": 1}}) == {"a": 1}
    assert qubic_stats.unwrap({"a": 1}) == {"a": 1}
    assert qubic_stats.unwrap({}) == {}


def test_poll_latest_stats_parses_official_fields(monkeypatch):
    rows = []
    payload = {
        "data": {
            "timestamp": "1790358375",
            "circulatingSupply": "177566139365105",
            "activeAddresses": 671275,
            "price": 4.48e-07,
            "marketCap": "79549631",
            "epoch": 232,
            "currentTick": 81669123,
            "ticksInCurrentEpoch": 269117,
            "emptyTicksInCurrentEpoch": 3933,
            "epochTickQuality": 98.53855,
            "burnedQus": "54433860634895",
            "ticksInLast10000": 10000,
            "emptyTicksInLast10000": 33,
            "last10000TickQuality": 99.67,
        }
    }
    monkeypatch.setattr(
        qubic_stats,
        "fetch_json",
        lambda *args, **kwargs: {"parsed": payload, "observation_id": "obs-1"},
    )
    monkeypatch.setattr(
        qubic_stats,
        "store_normalized",
        lambda table, chain, data, **kwargs: rows.append((table, data, kwargs)),
    )

    row, error = qubic_stats.poll_latest_stats()

    assert error is None
    assert row["active_addresses"] == 671275
    assert row["epoch_tick_quality"] == 98.53855
    assert row["last10000_tick_quality"] == 99.67
    assert row["burned_qus"] == 54433860634895
    assert row["circulating_supply"] == 177566139365105
    assert row["market_cap"] == 79549631
    assert row["epoch"] == 232
    assert row["source_role"] == "canonical"
    table, _data, kwargs = rows[0]
    assert table == "qubic_stats"
    assert kwargs["raw_event_id"] == "obs-1"


def test_poll_burn_events_is_idempotent(monkeypatch):
    purged = []
    written = []
    events = [
        {
            "epoch": 232,
            "tickNumber": 1,
            "logId": "1",
            "burning": {"source": "AAA", "amount": "10", "contractIndex": "1"},
        },
        {
            "epoch": 232,
            "tickNumber": 2,
            "logId": "2",
            "burning": {"source": "BBB", "amount": "20", "contractIndex": "1"},
        },
    ]

    monkeypatch.setattr(
        qubic_stats,
        "purge_normalized",
        lambda table, field, value: purged.append((table, field, value)) or 0,
    )
    monkeypatch.setattr(
        qubic_stats,
        "post_json",
        lambda url, body, **kwargs: (
            {"hits": {"total": 2}, "eventLogs": events},
            "obs-burn",
            None,
        ),
    )
    monkeypatch.setattr(
        qubic_stats,
        "store_normalized",
        lambda table, chain, data, **kwargs: written.append(data),
    )

    first, err = qubic_stats.poll_burn_events(232)
    second, err2 = qubic_stats.poll_burn_events(232)

    assert err is None and err2 is None
    assert purged == [("qubic_burn_event", "event_time", "232")] * 2
    assert len(written) == 4
    assert first["returned"] == 2
    assert second["returned"] == 2
    assert written[0]["burn_amount"] == "10"
    assert written[0]["source_id"] == "qubic-eventlog"


def test_poll_burn_events_requires_epoch(monkeypatch):
    called = []
    monkeypatch.setattr(
        qubic_stats, "purge_normalized", lambda *a, **k: called.append(a)
    )
    result, error = qubic_stats.poll_burn_events(None)
    assert result is None
    assert error == "no epoch"
    assert called == []


def test_run_pass_enriches_network_state(tmp_path, monkeypatch):
    netstate = tmp_path / "network_state.json"
    netstate.write_text(json.dumps({"QUBIC": {"epoch": 231}}))
    monkeypatch.setattr(qubic_stats, "NETSTATE_FILE", str(netstate))

    stats_row = {
        "epoch": 232,
        "active_addresses": 671275,
        "epoch_tick_quality": 98.5,
        "last10000_tick_quality": 99.6,
        "burned_qus": 54433860634895,
        "circulating_supply": 177566139365105,
        "market_cap": 79549631,
        "price": 4.48e-07,
    }
    monkeypatch.setattr(qubic_stats, "poll_latest_stats", lambda: (stats_row, None))
    monkeypatch.setattr(
        qubic_stats,
        "poll_burn_events",
        lambda epoch, **kwargs: ({"epoch": epoch}, None),
    )

    stats = qubic_stats.run_pass(qubic_stats.load_netstate())

    saved = json.loads(netstate.read_text())["QUBIC"]
    assert stats["latest_stats"] == "ok"
    assert saved["active_addresses"] == 671275
    assert saved["epoch_tick_quality"] == 98.5
    assert saved["burned_qus"] == 54433860634895
    assert saved["circulating_supply"] == 177566139365105
    assert saved["price_usd"] == 4.48e-07
    assert saved["burned_qus_source"] == "rpc.qubic.org/v1/latest-stats"
