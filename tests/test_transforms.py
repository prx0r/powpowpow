import json
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_insights as build_module

from transforms import (
    MIN_PUELL_SAMPLES,
    TRANSFORM_VERSION,
    active_address_growth,
    burn_profile,
    metric_vs_price_corr,
    price_hashrate_divergence,
    puell_multiple,
    security_spend_ratio,
    tick_quality_ribbon,
)


def price_rows(days=400, start_price=100.0, growth=0.001):
    start = date(2026, 1, 1)
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "close_usd": start_price * ((1 + growth) ** i),
            "symbol": "TEST",
        }
        for i in range(days)
    ]


def test_puell_multiple_computes_on_long_series():
    out = puell_multiple(
        price_rows(400),
        emission_per_day=10.0,
        window_days=365,
        emission_source="test emission",
    )
    assert out["refused"] is False
    assert out["metric"] == "puell_multiple"
    assert out["unit"] == "x"
    assert out["n"] == 400
    assert out["window"] == "365d"
    assert out["version"] == TRANSFORM_VERSION
    expected = 10.0 * price_rows(400)[-1]["close_usd"]
    assert abs(out["issuance_usd_day"] - expected) < 0.01


def test_puell_refuses_without_enough_history():
    out = puell_multiple(price_rows(50), emission_per_day=10.0, window_days=365)
    assert out["refused"] is True
    assert out["n"] == 50
    assert out["min_n"] == MIN_PUELL_SAMPLES
    assert "value" not in out


def test_puell_refuses_when_window_exceeds_history():
    out = puell_multiple(price_rows(250), emission_per_day=10.0, window_days=365)
    assert out["refused"] is True
    assert out["reason"] == "price history shorter than window"


def test_security_spend_ratio_refuses_without_supply_overlap():
    out = security_spend_ratio(
        price_rows(400), supply_rows=[], emission_per_day=10.0, window_days=365
    )
    assert out["refused"] is True
    assert out["metric"] == "security_spend_ratio"


def test_tick_quality_ribbon_refuses_then_computes():
    def rows(n):
        return [
            {
                "observed_at": f"2026-09-25T{i % 24:02d}:00:00Z",
                "last10000_tick_quality": 99.0 + (i % 3) * 0.1,
            }
            for i in range(n)
        ]

    refused = tick_quality_ribbon(rows(8))
    assert refused["refused"] is True
    assert refused["min_n"] == 13

    ok = tick_quality_ribbon(rows(20))
    assert ok["refused"] is False
    assert ok["metric"] == "tick_quality_ribbon"
    assert ok["above_mean"] in (True, False)
    assert ok["crosses_in_window"] >= 0


def test_active_address_growth_on_flat_series_is_zero_not_refused():
    series = [
        {"observed_at": f"2026-09-25T{hour:02d}:00:00Z", "active_addresses": 671275}
        for hour in range(6)
    ]
    out = active_address_growth(series)
    assert out["refused"] is False
    assert out["value"] == 0
    assert out["n"] == 6


def test_burn_profile_explains_epoch_start_burst():
    events = [
        {"epoch": 232, "tick_number": 100, "burn_amount": "385000000000"},
        {"epoch": 232, "tick_number": 101, "burn_amount": "385000000000"},
        {"epoch": 232, "tick_number": 50000, "burn_amount": "500000000"},
        {"epoch": 232, "tick_number": 90000, "burn_amount": "500000000"},
        {"epoch": 232, "tick_number": 120000, "burn_amount": "500000000"},
        {"epoch": 232, "tick_number": 150000, "burn_amount": "500000000"},
        {"epoch": 232, "tick_number": 180000, "burn_amount": "500000000"},
        {"epoch": 232, "tick_number": 210000, "burn_amount": "500000000"},
    ]
    metrics = {
        m["metric"]: m
        for m in burn_profile(events, initial_tick=100, scheduled_burn=800000000000)
    }

    total = metrics["burn_epoch_total"]
    assert total["refused"] is False
    assert total["value"] == sum(float(e["burn_amount"]) for e in events)

    deviation = metrics["burn_deviation_vs_schedule"]
    assert deviation["refused"] is False
    assert abs(deviation["value"] - total["value"] / 800000000000) < 1e-3
    assert deviation["scheduled_burn_qu"] == 800000000000

    concentration = metrics["burn_concentration_at_epoch_start"]
    assert concentration["value"] > 0.99
    assert concentration["burst_events"] == 2

    trickle = metrics["burn_trickle_rate"]
    assert trickle["refused"] is False
    assert trickle["trickle_events"] == 6
    assert trickle["unit"] == "QU per 1e6 ticks"


def test_burn_profile_refuses_thin_history():
    out = burn_profile([], initial_tick=None, scheduled_burn=None)
    assert len(out) == 1
    assert out[0]["refused"] is True


def test_price_hashrate_divergence_refuses_without_hashrate():
    out = price_hashrate_divergence(price_rows(400), [], window=30)
    assert out["refused"] is True
    assert out["metric"] == "price_hashrate_divergence"


def test_metric_vs_price_corr_refuses_below_minimum():
    short = [(f"2026-01-{i:02d}", float(i)) for i in range(1, 10)]
    out = metric_vs_price_corr(short, price_rows(400), window=30, metric_name="toy")
    assert out["refused"] is True
    assert out["n"] < out["min_n"]


def test_build_insights_writes_snapshot(tmp_path, monkeypatch):
    def fake_read(table, chain):
        if table == "price_history":
            return price_rows(400)
        if table == "chain_snapshot" and chain == "btc":
            return [
                {
                    "event_time": row["date"],
                    "circulating_supply": 19_000_000,
                    "network_hashrate_ths": 900000.0,
                }
                for row in price_rows(400)
            ]
        if table == "chain_snapshot" and chain == "xmr":
            return [
                {"observed_at": row["date"], "network_hashrate": 6e9}
                for row in price_rows(400)
            ]
        if table == "qubic_stats":
            return [
                {
                    "observed_at": f"2026-09-25T{h:02d}:00:00Z",
                    "last10000_tick_quality": 99.0 + h * 0.01,
                    "active_addresses": 600000 + h * 10,
                    "burned_qus": 1000 + h,
                    "current_tick": 100 + h,
                }
                for h in range(20)
            ]
        if table == "qubic_burn_event":
            return [
                {"epoch": 232, "tick_number": 100 + i * 1000, "burn_amount": "1000000"}
                for i in range(8)
            ]
        if table == "qubic_epoch":
            return [{"observed_at": "2026-09-25T00:00:00Z", "initial_tick": 100}]
        return []

    out = tmp_path / "insights.json"
    monkeypatch.setattr(build_module, "OUTPUT_FILE", str(out))
    monkeypatch.setattr(build_module, "read_table", fake_read)
    monkeypatch.setattr(
        build_module,
        "load_emission",
        lambda chain: (432.0, "test emission") if chain == "XMR" else (None, None),
    )

    payload = build_module.build()

    assert out.exists()
    stored = json.loads(out.read_text())
    assert stored["generated_at"] == payload["generated_at"]
    assert set(stored["chains"]) == {"BTC", "XMR", "QUBIC"}
    summary = stored["summary"]
    assert summary["metrics"] == summary["computed"] + summary["refused"]
    assert summary["computed"] > 0

    xmr_metrics = {m["metric"]: m for m in stored["chains"]["XMR"]["metrics"]}
    assert xmr_metrics["puell_multiple"]["refused"] is False
    qubic_metrics = {m["metric"]: m for m in stored["chains"]["QUBIC"]["metrics"]}
    assert qubic_metrics["price_hashrate_divergence"]["refused"] is True
