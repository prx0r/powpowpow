"""Tests for epoch_burn aggregation — pure logic on fixture rows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.epoch_burn import aggregate


def _row(ts, amt, epoch=232, contract="13"):
    return {"event_time_ms": ts, "amount": amt, "epoch": epoch,
            "contract": contract}


def test_genesis_excluded():
    out = aggregate([_row(1652445600000, 385_000_000_000, contract="6"),
                     _row(1790438764000, 25_069)])
    assert out["events_genesis_excluded"] == 1
    assert out["events_live"] == 1
    assert out["burn_total_live"] == 25_069
    assert out["genesis_total"] == 385_000_000_000


def test_per_day_none_for_single_point():
    out = aggregate([_row(1790438764000, 100)])
    assert out["burn_per_day_measured"] is None


def test_per_day_math():
    out = aggregate([_row(1790438764000, 100),
                     _row(1790438764000 + 2 * 86_400_000, 300)])
    assert out["burn_per_day_measured"] == 200.0


def test_garbage_rows_skipped():
    out = aggregate([{}, {"amount": "xyz"}, {"event_time_ms": "nope"}])
    assert out["events_live"] == 0
    assert out["burn_total_live"] == 0
