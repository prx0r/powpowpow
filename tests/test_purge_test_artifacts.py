import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import purge_test_artifacts


def test_purge_removes_only_test_trade_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    trade = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "trade"
        / "chain=venue"
        / "date=2026-01-01"
    )
    trade.mkdir(parents=True)
    hour = trade / "hour=00.jsonl"
    rows = [
        {"symbol": "X", "price": "1"},
        {"symbol": "BTC", "price": "2"},
        {"symbol": "X", "price": "3"},
    ]
    hour.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    removed = purge_test_artifacts.purge_trade_rows(apply=True)
    remaining = [json.loads(line) for line in hour.read_text().splitlines()]

    assert removed == 2
    assert remaining == [{"symbol": "BTC", "price": "2"}]


def test_purge_dry_run_leaves_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    trade = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "trade"
        / "chain=venue"
        / "date=2026-01-01"
    )
    trade.mkdir(parents=True)
    hour = trade / "hour=00.jsonl"
    hour.write_text(json.dumps({"symbol": "X"}) + "\n")

    would_remove = purge_test_artifacts.purge_trade_rows(apply=False)

    assert would_remove == 1
    assert len(hour.read_text().splitlines()) == 1


def test_purge_removes_only_test_raw_envelopes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "warehouse" / "raw" / "qubic"
    raw.mkdir(parents=True)
    test_file = raw / "aaa.json"
    real_file = raw / "bbb.json"
    test_file.write_text(json.dumps({"endpoint": "https://x"}))
    real_file.write_text(json.dumps({"endpoint": "https://rpc.qubic.org/v1"}))

    removed = purge_test_artifacts.purge_test_raw(apply=True)

    assert removed == 1
    assert not test_file.exists()
    assert real_file.exists()
