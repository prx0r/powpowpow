import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core
from signals import chain_symbol

_spec = importlib.util.spec_from_file_location(
    "pow_site_server", os.path.join(ROOT, "site", "server.py")
)
site_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_server)


def test_chain_symbol_strips_quote_suffixes():
    assert chain_symbol("XMRUSDT") == "XMR"
    assert chain_symbol("QUBICUSDT") == "QUBIC"
    assert chain_symbol("BTCUSDT") == "BTC"
    assert chain_symbol("PRLUSDC") == "PRL"
    assert chain_symbol("NOCKBTC") == "NOCK"
    assert chain_symbol("BTC") == "BTC"
    assert chain_symbol("") == ""


def test_purge_normalized_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setitem(core.purge_normalized.__globals__, "BASE_DIR", str(tmp_path))
    target = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "daily_state"
        / "chain=venue"
        / "date=2026-01-01"
    )
    target.mkdir(parents=True)
    hour = target / "hour=00.jsonl"
    rows = [
        {"date": "2026-01-01", "symbol": "BTC"},
        {"date": "2026-01-01", "symbol": "XMR"},
        {"date": "2026-01-02", "symbol": "QUBIC"},
    ]
    hour.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    first = core.purge_normalized("daily_state", "date", "2026-01-01")
    second = core.purge_normalized("daily_state", "date", "2026-01-01")
    remaining = [json.loads(line) for line in hour.read_text().splitlines()]

    assert first == 2
    assert second == 0
    assert remaining == [{"date": "2026-01-02", "symbol": "QUBIC"}]


def test_home_payload_shape():
    payload = site_server._home()

    assert set(payload["chains"]) == {"XMR", "QUBIC", "BTC"}
    for chain in payload["chains"].values():
        assert "price_usd" in chain
        assert "emission_usd_day" in chain
        assert "as_of" in chain
        assert "emission_source" in chain

    assert isinstance(payload["state"]["rows"], int)
    assert isinstance(payload["signals"]["today"], int)
    assert isinstance(payload["signals"]["top"], list)
    assert payload["health"]["ok"] in (True, False)
    assert "services" in payload["ops"]
    assert "heartbeats" in payload["ops"]


def test_home_signals_carry_numeric_z_scores():
    payload = site_server._home()
    for row in payload["signals"]["top"]:
        assert row.get("z") is not None
        assert isinstance(row.get("z"), (int, float))
