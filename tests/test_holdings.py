import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from transforms.holdings import (
    concentration_from_row,
    exchange_reserve,
    exchange_share_from_row,
    exchange_share_of_top_holders,
    gini,
    wealth_concentration,
)


def test_gini_of_equal_distribution_is_zero():
    assert gini([100, 100, 100, 100]) == 0.0


def test_gini_rises_with_concentration():
    flat = gini([100, 100, 100, 100])
    skewed = gini([0, 0, 0, 100])
    assert skewed == 0.75
    assert skewed > flat


def test_exchange_reserve_refuses_without_rows():
    out = exchange_reserve([])
    assert out["refused"] is True
    assert out["metric"] == "exchange_reserve"


def test_exchange_reserve_computes_share_of_supply():
    rows = [
        {"name": "Gate.io", "balance": 700},
        {"name": "MEXC", "balance": 200},
        {"name": "CoinEx", "balance": 100},
    ]
    out = exchange_reserve(rows, circulating_supply=5000)
    assert out["refused"] is False
    assert out["value"] == 1000
    assert out["share_of_supply_pct"] == 20.0
    assert out["entities"] == 3
    assert out["largest"] == "Gate.io"
    assert out["breakdown"][0]["name"] == "Gate.io"
    assert abs(out["breakdown"][0]["share"] - 0.7) < 1e-9


def test_exchange_reserve_omits_supply_share_when_missing():
    out = exchange_reserve([{"name": "X", "balance": 5}])
    assert out["refused"] is False
    assert "share_of_supply" not in out


def test_wealth_concentration_refuses_thin_list():
    out = wealth_concentration([1, 2, 3])
    assert out["refused"] is True
    assert out["min_n"] == 100


def test_wealth_concentration_reports_shares():
    balances = [1_000_000] + [1_000] * 999
    out = wealth_concentration(balances)
    assert out["refused"] is False
    assert out["metric"] == "wealth_concentration"
    assert out["n"] == 1000
    assert out["unit"] == "gini"
    shares = out["shares"]
    assert shares["top_1pct_n"] == 10
    assert 0.50 < shares["top_1pct"] < 0.51
    assert shares["top_20pct_n"] == 200
    assert 0.74 < shares["top_50pct"] < 0.76
    assert out["mean_to_median"] > 1


def test_exchange_share_of_top_holders_counts_labelled():
    exchanges = ["AAAA", "BBBB"]
    rich = [
        {"identity": "AAAA", "balance": 10},
        {"identity": "CCCC", "balance": 90},
        {"identity": "BBBB", "balance": 10},
        {"identity": "DDDD", "balance": 10},
    ]
    out = exchange_share_of_top_holders(exchanges, rich)
    assert out["refused"] is False
    assert out["value"] == 0.5
    assert out["labelled_in_top"] == 2
    assert abs(out["labelled_balance_share"] - 20 / 120) < 1e-3


def test_exchange_share_refuses_missing_inputs():
    assert exchange_share_of_top_holders([], [{"identity": "A"}])["refused"]
    assert exchange_share_of_top_holders(["A"], [])["refused"]


def test_snapshot_row_helpers():
    row = {
        "gini": 0.8745,
        "holders": 10000,
        "epoch": 232,
        "total_held": 10**15,
        "mean_balance": 10**11,
        "median_balance": 10**9,
        "mean_to_median": 100.0,
        "shares": {"top_1pct": 0.64},
        "exchange_share_of_top_holders": 0.0007,
        "exchange_labelled_in_top": 7,
    }
    concentration = concentration_from_row(row)
    assert concentration["refused"] is False
    assert concentration["value"] == 0.8745
    assert concentration["n"] == 10000
    assert concentration["epoch"] == 232
    assert concentration["shares"]["top_1pct"] == 0.64

    share = exchange_share_from_row(row)
    assert share["refused"] is False
    assert share["value"] == 0.0007
    assert share["labelled_in_top"] == 7
    assert "exchanges.json" in share["registry"]

    assert concentration_from_row(None)["refused"] is True
    assert exchange_share_from_row(None)["refused"] is True


def test_exchange_reserve_marks_partial_when_incomplete():
    rows = [{"name": "Gate.io", "balance": 100}]
    out = exchange_reserve(rows, circulating_supply=1000, expected_entities=3)

    assert out["refused"] is False
    assert out["partial"] is True
    assert out["expected_entities"] == 3
    assert out["missing_entities"] == 2
    assert "partial" in out["window"]
    assert "share_of_supply" not in out
