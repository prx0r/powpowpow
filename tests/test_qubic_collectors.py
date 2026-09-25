import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from collectors import qubic_holdings, qubic_transfers


def test_aggregate_counts_addresses_and_exchange_flows():
    events = [
        {
            "epoch": 232,
            "tickNumber": 100,
            "timestamp": "1790000000000",
            "logId": "1",
            "quTransfer": {
                "source": "EXCHANGE_A",
                "destination": "USER_1",
                "amount": "500",
            },
        },
        {
            "epoch": 232,
            "tickNumber": 200,
            "timestamp": "1790000060000",
            "logId": "2",
            "quTransfer": {
                "source": "USER_2",
                "destination": "EXCHANGE_A",
                "amount": "250",
            },
        },
        {
            "epoch": 232,
            "tickNumber": 300,
            "timestamp": "1790000120000",
            "logId": "3",
            "quTransfer": {
                "source": "USER_3",
                "destination": "WHALE_DEST",
                "amount": "2000000000",
            },
        },
    ]

    row = qubic_transfers.aggregate(events, {"EXCHANGE_A"})

    assert row["n_transfers"] == 3
    assert row["unique_addresses"] == 5
    assert row["exchange_inflow"] == 500
    assert row["exchange_outflow"] == 250
    assert row["exchange_netflow"] == -250
    assert row["whale_count"] == 1
    assert row["whale_volume"] == 2000000000
    assert row["total_volume"] == 2000000750
    assert row["tick_from"] == 100
    assert row["tick_to"] == 300
    assert row["window_seconds"] == 120.0
    assert row["source_id"] == "qubic-eventlog"
    assert "recoverability" not in row  # store_normalized stamps it


def test_aggregate_ignores_transfers_without_amount():
    events = [
        {
            "tickNumber": 1,
            "timestamp": "1",
            "quTransfer": {"source": "A", "destination": "B", "amount": "not-a-number"},
        },
    ]
    assert qubic_transfers.aggregate(events, set()) is None
    assert qubic_transfers.aggregate([], set()) is None


def test_load_exchange_identities_from_cache(tmp_path, monkeypatch):
    registry = tmp_path / "qubic_exchanges.json"
    registry.write_text(
        json.dumps(
            {
                "exchanges": [
                    {"name": "Gate.io", "address": "AAAA"},
                    {"name": "MEXC", "address": "BBBB"},
                ],
            }
        )
    )
    monkeypatch.setattr(qubic_transfers, "REGISTRY_FILE", str(registry))

    assert qubic_transfers.load_exchange_identities() == {"AAAA", "BBBB"}


def test_load_exchange_identities_empty_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        qubic_transfers, "REGISTRY_FILE", str(tmp_path / "missing.json")
    )

    assert qubic_transfers.load_exchange_identities() == set()


def test_poll_exchange_balances_stores_rows_and_totals(monkeypatch):
    rows = []

    def fake_fetch(url, **kwargs):
        identity = url.rsplit("/", 1)[-1]
        return {
            "parsed": {
                "balance": {"id": identity, "balance": "1000", "validForTick": 77}
            },
            "observation_id": f"obs-{identity}",
        }

    monkeypatch.setattr(qubic_holdings, "fetch_json", fake_fetch)
    monkeypatch.setattr(
        qubic_holdings,
        "store_normalized",
        lambda table, chain, data, **kwargs: rows.append((table, data, kwargs)),
    )

    exchanges = [
        {"name": "Gate.io", "address": "ADDR1"},
        {"name": "MEXC", "address": "ADDR2"},
    ]
    result, error = qubic_holdings.poll_exchange_balances(exchanges)

    assert error is None
    assert result == {"entities": 2, "total": 2000}
    assert len(rows) == 2
    table, data, kwargs = rows[0]
    assert table == "qubic_exchange_balance"
    assert data["balance"] == 1000
    assert data["valid_for_tick"] == 77
    assert data["source_role"] == "canonical"
    assert kwargs["raw_event_id"] == "obs-ADDR1"


def test_poll_exchange_balances_reports_missing_registry():
    result, error = qubic_holdings.poll_exchange_balances([])
    assert result is None
    assert error == "no exchange registry"
