import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import factors


def _setup(tmp_path, monkeypatch, symbol="BTCUSDT"):
    chains = tmp_path / "chains"
    factors_dir = chains / "factors"
    factors_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(factors, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(factors, "CHAINS_DIR", str(chains))
    monkeypatch.setattr(factors, "FACTORS_DIR", str(factors_dir))

    (chains / "chain_fundamentals.json").write_text(
        json.dumps(
            {
                "BTC": {"daily_emission": 450.0, "name": "Bitcoin"},
                "XMR": {"daily_emission": 432.0, "name": "Monero"},
            }
        )
    )
    (chains / "network_state.json").write_text(json.dumps({}))

    state_dir = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "daily_state"
        / "chain=safetrade"
        / "date=2026-09-25"
    )
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "hour=00.jsonl").write_text(
        json.dumps(
            {
                "date": "2026-09-25",
                "venue": "safetrade",
                "symbol": symbol,
                "bid_notional_20_mean": 100.0,
                "ask_notional_20_mean": 110.0,
                "mid_close": 80000.0,
                "spread_bps_median": 12.0,
                "trade_notional_sum": 500.0,
                "n_trades": 10,
                "observed_at": "2026-09-25T10:00:00Z",
            }
        )
        + "\n"
    )
    return factors_dir


def test_factors_resolve_chain_keys_for_venue_symbols(tmp_path, monkeypatch):
    factors_dir = _setup(tmp_path, monkeypatch)

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    venue = result["BTCUSDT"]
    assert venue["chain_symbol"] == "BTC"
    assert venue["daily_emission_native"] == 450.0
    assert venue["issuance_usd_24h"] == 36_000_000.0
    assert venue["burden_vs_book"] == 360000.0
    assert venue["name"] == "Bitcoin"

    # SafeTrade is not BTC's venue of truth, so the chain row publishes the
    # refusal instead of a ratio computed off a $168 book.
    alias = result["BTC"]
    assert alias["symbol"] == "BTC"
    assert alias["venue_symbol"] == "BTCUSDT"
    assert alias["burden_vs_book"] is None
    assert alias["market_coverage_refusal"] == "depth_not_venue_of_truth: safetrade"


def test_factors_carry_forward_untouched_chain_rows(tmp_path, monkeypatch):
    factors_dir = _setup(tmp_path, monkeypatch)
    existing = {
        "KAS": {
            "symbol": "KAS",
            "burden_vs_book": 11.5,
            "issuance_usd_24h": 74262.77,
            "timestamp": "2026-09-24T00:00:00Z",
        },
        "BTC": {"symbol": "BTC", "burden_vs_book": 1.0},
    }
    (factors_dir / "cross_chain_factors.json").write_text(json.dumps(existing))

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    assert result["KAS"]["burden_vs_book"] == 11.5
    assert result["KAS"]["carried_forward"] is True
    assert result["KAS"]["carried_forward_at"] == "2026-09-24T00:00:00Z"
    assert "carried_forward" not in result["BTC"]
    # recomputed for 2026-09-25, so the stale carried value never survives
    assert result["BTC"]["burden_vs_book"] is None


def test_chain_alias_prefers_usdt_market(tmp_path, monkeypatch):
    factors_dir = _setup(tmp_path, monkeypatch, symbol="XMRUSDT")
    state_dir = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "daily_state"
        / "chain=safetrade"
        / "date=2026-09-25"
    )
    with (state_dir / "hour=00.jsonl").open("a") as handle:
        handle.write(
            json.dumps(
                {
                    "date": "2026-09-25",
                    "venue": "safetrade",
                    "symbol": "XMRBTC",
                    "bid_notional_20_mean": 10.0,
                    "ask_notional_20_mean": 11.0,
                    "mid_close": 0.007,
                    "spread_bps_median": 20.0,
                    "observed_at": "2026-09-25T10:01:00Z",
                }
            )
            + "\n"
        )

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    assert result["XMR"]["venue_symbol"] == "XMRUSDT"
    assert result["XMRUSDT"]["daily_emission_native"] == 432.0


def _append_state(tmp_path, row):
    state_dir = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "daily_state"
        / "chain=safetrade"
        / "date=2026-09-25"
    )
    with (state_dir / "hour=00.jsonl").open("a") as handle:
        handle.write(json.dumps(row) + "\n")


def test_chain_row_aggregates_depth_across_pairs(tmp_path, monkeypatch):
    factors_dir = _setup(tmp_path, monkeypatch, symbol="XMRUSDT")
    _append_state(
        tmp_path,
        {
            "date": "2026-09-25",
            "venue": "safetrade",
            "symbol": "XMRUSDC",
            "bid_notional_20_mean": 50.0,
            "ask_notional_20_mean": 55.0,
            "mid_close": 80000.0,
            "spread_bps_median": 40.0,
            "observed_at": "2026-09-25T10:02:00Z",
        },
    )

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    chain = result["XMR"]
    assert chain["venue_symbol"] == "XMRUSDT"  # preferred pair kept
    assert chain["bid_notional_20_sum"] == 150.0  # USDT + USDC summed
    assert chain["depth_pairs"] == ["XMRUSDC", "XMRUSDT"]
    assert chain["burden_vs_book"] is None  # safetrade-only refusal
    assert "depth_not_venue_of_truth" in chain["market_coverage_refusal"]

    # A primary venue contributing depth lifts the refusal and the ratio returns.
    (factors_dir.parent / "factors").mkdir(parents=True, exist_ok=True)
    venue_dir = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "daily_state"
        / "chain=venue"
        / "date=2026-09-25"
    )
    venue_dir.mkdir(parents=True, exist_ok=True)
    (venue_dir / "hour=00.jsonl").write_text(
        json.dumps(
            {
                "date": "2026-09-25",
                "venue": "kraken",
                "symbol": "xmrusd",
                "bid_notional_20_mean": 1000.0,
                "ask_notional_20_mean": 1100.0,
                "mid_close": 80000.0,
                "spread_bps_median": 5.0,
                "observed_at": "2026-09-25T10:03:00Z",
            }
        )
        + "\n"
    )

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    chain = result["XMR"]
    assert chain["market_coverage_refusal"] is None
    assert chain["bid_notional_20_sum"] == 1150.0
    assert round(chain["burden_vs_book"], 3) == round(432.0 * 80000.0 / 1150.0, 3)


def test_chain_row_converts_non_usd_quote_depth(tmp_path, monkeypatch):
    factors_dir = _setup(tmp_path, monkeypatch, symbol="XMRUSDT")
    chains = tmp_path / "chains"
    (chains / "network_state.json").write_text(
        json.dumps({"BTC": {"price_usd": 80000.0}})
    )
    _append_state(
        tmp_path,
        {
            "date": "2026-09-25",
            "venue": "safetrade",
            "symbol": "XMRBTC",
            "bid_notional_20_mean": 0.04,
            "ask_notional_20_mean": 0.05,
            "mid_close": 0.007,
            "spread_bps_median": 20.0,
            "observed_at": "2026-09-25T10:04:00Z",
        },
    )

    factors.compute_factors("2026-09-25")
    result = json.loads((factors_dir / "cross_chain_factors.json").read_text())

    pair = result["XMRBTC"]
    assert pair["quote_currency"] == "BTC"
    assert pair["bid_notional_20_sum"] == 3200.0  # 0.04 BTC @ 80k
    assert pair["price_usd"] == 560.0  # 0.007 BTC @ 80k
    assert pair["price_native"] == 0.007
    # ratio survives conversion (both sides scale by the BTC price)
    assert pair["burden_vs_book"] is not None
    assert result["XMR"]["bid_notional_20_sum"] == 3300.0  # 100 USDT + 3,200
