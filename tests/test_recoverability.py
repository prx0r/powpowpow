import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core
import manifest
from collectors.l2_archival import tracked_ticker_rows


def test_classify_recoverability_by_source_and_table():
    assert (
        core.classify_recoverability("price_history", "coingecko") == "reconstructable"
    )
    assert (
        core.classify_recoverability(
            "chain_snapshot", "blockchaininfo-charts/hash-rate"
        )
        == "reconstructable"
    )
    assert core.classify_recoverability("qubic_epoch", "qubic-rpc") == "reconstructable"
    assert core.classify_recoverability("daily_state", None) == "derived"
    assert core.classify_recoverability("derived_signal", "x") == "derived"
    assert core.classify_recoverability("orderbook_snapshot", None) == "ephemeral"
    assert (
        core.classify_recoverability("pool_snapshot", "p2pool-observer") == "ephemeral"
    )
    assert core.classify_recoverability(None, None) == "ephemeral"


def test_store_normalized_stamps_recoverability(tmp_path, monkeypatch):
    monkeypatch.setitem(core.store_normalized.__globals__, "BASE_DIR", str(tmp_path))

    core.store_normalized(
        "price_history", "xmr", {"symbol": "XMR", "source_id": "coingecko"}
    )
    core.store_normalized("orderbook_snapshot", "safetrade", {"symbol": "btcusdt"})
    core.store_normalized(
        "daily_state", "venue", {"symbol": "BTC", "date": "2026-09-25"}
    )

    got = {}
    for path in (tmp_path / "warehouse" / "normalized").rglob("hour=*.jsonl"):
        table = path.relative_to(tmp_path / "warehouse" / "normalized").parts[0]
        for line in path.read_text().splitlines():
            row = json.loads(line)
            got.setdefault(table, row["recoverability"])

    assert got["price_history"] == "reconstructable"
    assert got["orderbook_snapshot"] == "ephemeral"
    assert got["daily_state"] == "derived"


def test_tracked_ticker_rows_drops_untracked_markets():
    payload = {
        "btcusdt": {"last": "86000", "volume": "12.5"},
        "xmrusdt": {"last": "570", "volume": "3"},
        "someotherusdt": {"last": "1", "volume": "2"},
    }
    rows = tracked_ticker_rows(payload, ["btcusdt", "xmrusdt"])
    assert [m for m, _ in rows] == ["btcusdt", "xmrusdt"]
    assert rows[0][1]["last"] == "86000"


def test_tracked_ticker_rows_handles_list_payload():
    payload = [
        {"market": "PRLUSDT", "last": "0.12", "volume": "900"},
        {"id": "KASUSDT", "last": "0.04"},
    ]
    rows = tracked_ticker_rows(payload, ["prlusdt"])
    assert rows == [("prlusdt", payload[0])]


def test_manifest_paths_point_at_this_checkout():
    assert manifest.WAREHOUSE_DIR == os.path.join(ROOT, "warehouse")
    assert manifest.MANIFEST_DIR == os.path.join(ROOT, "warehouse", "manifests")
    assert os.path.isdir(manifest.WAREHOUSE_DIR)


def test_manifest_layer_mapping():
    assert (
        manifest._layer_for_record(
            "price_history", {"recoverability": "reconstructable"}
        )
        == "canonical_backfill"
    )
    assert (
        manifest._layer_for_record(
            "orderbook_snapshot", {"recoverability": "ephemeral"}
        )
        == "ephemeral_archive"
    )
    assert (
        manifest._layer_for_record("daily_state", {"recoverability": "derived"})
        == "derived"
    )
    assert (
        manifest._layer_for_record("price_history", {"source_id": "coingecko"})
        == "canonical_backfill"
    )
    assert manifest._layer_for_record(None, None) == "unknown"
