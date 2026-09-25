import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import signals  # noqa: E402

T0 = "2026-09-25T10:00:00Z"
T1 = "2026-09-25T11:00:00Z"


def row(symbol, venue, bid, mid, trades=100, volume=1000.0, at=T0, rec=None):
    return {
        "symbol": symbol,
        "venue": venue,
        "bid_notional_20_mean": bid,
        "ask_notional_20_mean": bid * 1.1,
        "mid_close": mid,
        "spread_bps_median": 100.0,
        "trade_notional_sum": volume,
        "n_trades": trades,
        "record_id": rec or f"rec-{symbol}-{venue}",
        "observed_at": at,
    }


def _run(monkeypatch, rows, emissions, prices=None, capsys=None):
    by_chain = {
        "venue": [r for r in rows if r["venue"] != "safetrade"],
        "safetrade": [r for r in rows if r["venue"] == "safetrade"],
    }
    monkeypatch.setattr(
        signals, "read_states", lambda date, chain="venue": by_chain.get(chain, [])
    )
    monkeypatch.setattr(
        signals, "load_emission", lambda sym: (emissions.get(sym), "test-fundamentals")
    )
    monkeypatch.setattr(signals, "load_quote_prices", lambda: prices or {})
    monkeypatch.setattr(signals, "store_normalized", lambda *a, **k: None)
    return signals.build_signals("2026-09-25")


def test_split_symbol_returns_quote():
    assert signals.split_symbol("PRLBTC") == ("PRL", "BTC")
    assert signals.split_symbol("XMRUSD") == ("XMR", "USD")
    assert signals.split_symbol("prlusdt") == ("PRL", "USDT")
    assert signals.split_symbol("PRL") == ("PRL", None)


def test_to_usd_converts_and_refuses_unknown_quotes():
    assert signals.to_usd(100.0, "USDT", {}) == 100.0
    assert signals.to_usd(100.0, None, {}) == 100.0
    assert signals.to_usd(0.04, "BTC", {"BTC": 80000.0}) == 3200.0
    assert signals.to_usd(1.0, "SAFE", {}) is None
    assert signals.to_usd(None, "BTC", {"BTC": 1.0}) is None


def test_secondary_depth_gate():
    assert signals.depth_venues_are_primary("PRL", {"safetrade"}) is True
    assert signals.depth_venues_are_primary("BTC", {"safetrade"}) is False
    assert signals.depth_venues_are_primary("BTC", {"safetrade", "coinbase"}) is True
    assert signals.depth_venues_are_primary("XMR", {"kraken"}) is True


def test_signals_aggregate_pairs_to_chain(monkeypatch):
    emissions = {"PRL": 500000.0, "QUBIC": 1e9, "NOCK": 1000.0, "XEL": 500.0}
    rows = [
        row("PRLUSDT", "safetrade", 5000.0, 1.08, trades=500, volume=400000.0),
        row("PRLUSDC", "safetrade", 14000.0, 1.08, trades=11, volume=0.0, at=T1),
        row("QUBICUSDT", "safetrade", 300.0, 4.3e-7, trades=89, volume=17000.0),
        row("NOCKUSDT", "safetrade", 900.0, 0.028, trades=46, volume=6000.0),
        row("XELUSDT", "safetrade", 700.0, 0.38, trades=6, volume=28.0),
    ]
    out = _run(monkeypatch, rows, emissions)

    assets = {s["asset"] for s in out}
    assert "PRL" in assets and "PRLUSDT" not in assets

    prl = next(s for s in out if s["asset"] == "PRL")
    assert prl["drivers"][1] == "bid_notional_20_sum=19,000"
    assert prl["evidence"]["depth_pairs"] == ["PRLUSDC", "PRLUSDT"]
    assert prl["evidence"]["depth_venues"] == ["safetrade"]


def test_signals_refuse_secondary_only_depth(monkeypatch, capsys):
    emissions = {
        "BTC": 450.0,
        "PRL": 500000.0,
        "QUBIC": 1e9,
        "NOCK": 1000.0,
        "XEL": 500.0,
    }
    rows = [
        row("BTCUSDT", "safetrade", 168.0, 83000.0, trades=89, volume=15000.0),
        row("PRLUSDT", "safetrade", 5000.0, 1.08, trades=500, volume=400000.0),
        row("QUBICUSDT", "safetrade", 300.0, 4.3e-7, trades=89, volume=17000.0),
        row("NOCKUSDT", "safetrade", 900.0, 0.028, trades=46, volume=6000.0),
        row("XELUSDT", "safetrade", 700.0, 0.38, trades=6, volume=28.0),
    ]
    out = _run(monkeypatch, rows, emissions)

    assert "BTC" not in {s["asset"] for s in out}
    assert "refused BTC: depth_not_venue_of_truth: safetrade" in capsys.readouterr().out

    # ...and is scored as soon as a primary venue contributes depth.
    rows.append(row("BTCUSD", "coinbase", 5_000_000.0, 83000.0, trades=100, volume=0.0))
    out = _run(monkeypatch, rows, emissions)
    btc = next(s for s in out if s["asset"] == "BTC")
    assert btc["evidence"]["depth_venues"] == ["coinbase", "safetrade"]


def test_signals_refuse_depth_below_resolution(monkeypatch, capsys):
    emissions = {
        "DUST": 1000.0,
        "PRL": 500000.0,
        "QUBIC": 1e9,
        "NOCK": 1000.0,
        "XEL": 500.0,
    }
    rows = [
        row("DUSTUSDT", "safetrade", 12.0, 1.0, trades=1, volume=5.0),
        row("PRLUSDT", "safetrade", 5000.0, 1.08, trades=500, volume=400000.0),
        row("QUBICUSDT", "safetrade", 300.0, 4.3e-7, trades=89, volume=17000.0),
        row("NOCKUSDT", "safetrade", 900.0, 0.028, trades=46, volume=6000.0),
        row("XELUSDT", "safetrade", 700.0, 0.38, trades=6, volume=28.0),
    ]
    out = _run(monkeypatch, rows, emissions)

    assert "DUST" not in {s["asset"] for s in out}
    assert "refused DUST: bid_below_resolution" in capsys.readouterr().out


def test_signals_refuse_tiny_cross_section(monkeypatch, capsys):
    emissions = {"PRL": 500000.0}
    rows = [row("PRLUSDT", "safetrade", 5000.0, 1.08)]
    assert _run(monkeypatch, rows, emissions) == []
    assert "insufficient cross-section (1 markets)" in capsys.readouterr().out


def test_btc_quote_depth_converts_to_usd(monkeypatch):
    emissions = {"PRL": 500000.0, "QUBIC": 1e9, "NOCK": 1000.0, "XEL": 500.0}
    rows = [
        row("PRLUSDT", "safetrade", 5000.0, 1.08, trades=500, volume=400000.0),
        row("PRLBTC", "safetrade", 0.04, 1.4e-5, trades=1, volume=0.0, at=T1),
        row("QUBICUSDT", "safetrade", 300.0, 4.3e-7, trades=89, volume=17000.0),
        row("NOCKUSDT", "safetrade", 900.0, 0.028, trades=46, volume=6000.0),
        row("XELUSDT", "safetrade", 700.0, 0.38, trades=6, volume=28.0),
    ]
    out = _run(monkeypatch, rows, emissions, prices={"BTC": 80000.0})

    prl = next(s for s in out if s["asset"] == "PRL")
    # 5,000 USDT + 0.04 BTC @ 80,000 = 5,000 + 3,200
    assert prl["drivers"][1] == "bid_notional_20_sum=8,200"
