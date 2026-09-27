"""Tests for daily_brief helpers — pure logic, no warehouse needed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.daily_brief import brief_tape, flag, latest_before, num


def test_num():
    assert num("3.5") == 3.5
    assert num(None) is None
    assert num("xyz") is None


def test_flag_scores():
    f = flag("t", 2, 3, 2, "TAPE")
    assert f["score"]["total"] == 12


def test_latest_before():
    rows = [{"observed_at": "2026-09-26T00:00:00Z", "v": 1},
            {"observed_at": "2026-09-27T00:00:00Z", "v": 2}]
    assert latest_before(rows, 1_789_000_000)["v"] == 2
    assert latest_before(rows, 1_780_000_000) is None
    assert latest_before([], 99) is None


def test_tape_seller_dominance():
    factors = {"X": {"trade_buy_notional": 100, "trade_sell_notional": 300,
                     "trade_notional_24h": 400}}
    flags = brief_tape("X", 0, factors)
    assert any("sellers 3.0x" in f["text"] for f in flags)


def test_tape_quiet():
    factors = {"X": {"trade_buy_notional": 100, "trade_sell_notional": 100,
                     "trade_notional_24h": 200, "burden_vs_book": 1.0,
                     "spread_bps_median": 10}}
    assert brief_tape("X", 0, factors) == []
