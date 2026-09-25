import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import collectors.depth_snapshots as ds  # noqa: E402

COINBASE = {
    "bids": [["83000.0", "1.5", 3], ["82999.0", "2.0", 1]],
    "asks": [["83001.0", "1.0", 2]],
}
KRAKEN = {
    "error": [],
    "result": {
        "XXMRZUSD": {
            "bids": [["555.0", "10.0", 1790000000], ["554.0", "20.0", 1790000001]],
            "asks": [["556.0", "5.0", 1790000002]],
        }
    },
}


def test_metrics_mid_spread_and_top20_notional():
    mid, spread, bid, ask = ds.metrics(
        [["100.0", "1.0"], ["99.0", "2.0"]], [["101.0", "1.0"]]
    )
    assert mid == 100.5
    assert round(spread, 4) == round((101 - 100) / 100.5 * 10000, 4)
    assert bid == 100.0 + 198.0  # 100x1 + 99x2
    assert ask == 101.0


def test_metrics_handles_empty_and_junk():
    # empty book: no quotes to price, but zero depth is a real measurement
    assert ds.metrics([], []) == (None, None, 0, 0)
    # unparseable levels refuse the whole snapshot rather than report 0
    assert ds.metrics([["x", "y"]], [["1", "1"]]) == (None, None, None, None)


def test_parse_coinbase_and_kraken():
    bids, asks, _ = ds.parse_coinbase(COINBASE)
    assert bids[0] == ["83000.0", "1.5"]  # num_orders column dropped
    assert len(asks) == 1

    bids, asks, _ = ds.parse_kraken(KRAKEN)
    assert bids[0] == ["555.0", "10.0"]
    assert len(asks) == 1


def test_parse_rejects_error_and_non_dict():
    assert ds.parse_kraken({"error": ["EQuery:Unknown asset pair"]}) is None
    assert ds.parse_kraken({"error": [], "result": {}}) is None
    assert ds.parse_coinbase(None) is None
    assert ds.parse_coinbase([1, 2, 3]) is None


def test_poll_writes_normalized_row(monkeypatch):
    written = {}

    monkeypatch.setattr(
        ds,
        "fetch_json",
        lambda *a, **k: {"parsed": COINBASE, "observation_id": "obs-1"},
    )
    monkeypatch.setattr(
        ds,
        "store_normalized",
        lambda table, chain, row, **k: written.update(
            {"table": table, "chain": chain, "row": row}
        ),
    )

    out = ds.poll(
        "coinbase",
        {"pair": "BTC-USD", "symbol": "btcusd"},
        "coinbase-depth",
        "2026-09-25T10:00:00Z",
    )

    assert out["ok"] is True
    assert out["bid"] == 83000.0 * 1.5 + 82999.0 * 2.0
    assert written["table"] == "orderbook_snapshot"
    assert written["chain"] == "venue"
    row = written["row"]
    assert row["venue"] == "coinbase"
    assert row["symbol"] == "btcusd"
    assert row["market"] == "BTC-USD"
    assert row["snapshot_kind"] == "rest_poll"
    assert row["raw_event_id"] == "obs-1"
    assert row["bid_notional_20"] == out["bid"]
    assert len(row["bids"]) == 2


def test_poll_reports_unparseable_payload(monkeypatch):
    monkeypatch.setattr(
        ds,
        "fetch_json",
        lambda *a, **k: {"parsed": {"error": ["boom"]}, "observation_id": "obs-2"},
    )
    monkeypatch.setattr(
        ds,
        "store_normalized",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    out = ds.poll(
        "kraken",
        {"pair": "XMRUSD", "symbol": "xmrusd"},
        "kraken-depth",
        "2026-09-25T10:00:00Z",
    )
    assert out == {"ok": False, "reason": "unparseable_payload"}


def test_cycle_survives_source_failure(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(a)
        raise RuntimeError("network down")

    monkeypatch.setattr(ds, "fetch_json", boom)
    monkeypatch.setattr(ds, "store_normalized", lambda *a, **k: None)
    monkeypatch.setattr(ds, "write_heartbeat", lambda state: None)

    state = {"polls": 0, "ok": 0, "failed": 0, "last": {}}
    results = ds.cycle(state)

    assert len(results) == len(ds.SOURCES)
    assert state["failed"] == len(ds.SOURCES)
    assert all(not r["ok"] for r in results)
    assert "network down" in state["last"]["coinbase:btcusd"]["reason"]
