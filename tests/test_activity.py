import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transforms.activity import activity_metrics


def window_row(**overrides):
    row = {
        "observed_at": "2026-09-25T18:00:00Z",
        "epoch": 232,
        "tick_from": 100,
        "tick_to": 241,
        "window_seconds": 102.0,
        "n_transfers": 1000,
        "unique_addresses": 80,
        "total_volume": 1_766_578_355,
        "max_amount": 268_701_925,
        "exchange_inflow": 231_734_718,
        "exchange_outflow": 0,
        "exchange_netflow": -231_734_718,
        "whale_count": 0,
        "whale_volume": 0,
        "whale_share_of_volume": 0.0,
    }
    row.update(overrides)
    return row


def test_activity_metrics_empty_refuses():
    out = activity_metrics([])
    assert len(out) == 1
    assert out[0]["refused"] is True
    assert out[0]["metric"] == "measured_active_addresses"


def test_activity_metrics_reports_measured_addresses_and_rate():
    out = activity_metrics([window_row()])
    metrics = {m["metric"]: m for m in out}

    addresses = metrics["measured_active_addresses"]
    assert addresses["refused"] is False
    assert addresses["value"] == 80
    assert addresses["n"] == 1000
    assert addresses["unit"] == "addresses in window"
    assert addresses["version"]
    assert addresses["extra" if "extra" in addresses else "note"].startswith("measured")

    rate = metrics["transfer_rate"]
    assert rate["refused"] is False
    assert abs(rate["value"] - 1000 / 102.0 * 60) < 0.01

    netflow = metrics["exchange_netflow"]
    assert netflow["value"] == -231_734_718
    assert netflow["extra" if "extra" in netflow else "exchange_inflow"] == 231_734_718
    assert "netflow_delta" not in netflow

    whale = metrics["whale_share_of_volume"]
    assert whale["value"] == 0.0
    assert whale["unit"] == "share of window volume"


def test_exchange_netflow_carries_delta_against_previous_window():
    previous = window_row(
        observed_at="2026-09-25T17:55:00Z", exchange_netflow=-100_000_000
    )
    current = window_row(
        observed_at="2026-09-25T18:00:00Z", exchange_netflow=-231_734_718
    )
    out = activity_metrics([previous, current])
    netflow = next(m for m in out if m["metric"] == "exchange_netflow")
    assert netflow["netflow_delta"] == -131_734_718
    assert netflow["sign_convention"].startswith("positive")


def test_activity_metrics_refuses_window_without_address_count():
    out = activity_metrics([window_row(unique_addresses=None)])
    assert out[0]["refused"] is True
    assert out[0]["reason"] == "window has no address count"
