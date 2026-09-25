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

    alias = result["BTC"]
    assert alias["symbol"] == "BTC"
    assert alias["venue_symbol"] == "BTCUSDT"
    assert alias["burden_vs_book"] == 360000.0


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
    assert result["BTC"]["burden_vs_book"] == 360000.0


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
