"""Tests for burn_snapshot helpers — pure logic, no network."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.burn_snapshot import burn_rate_per_day


def test_burn_rate_basic():
    older = {"burned_total": "54433860634895", "timestamp": "1790432862"}
    newer = {"burned_total": "54456360634895", "timestamp": str(1790432862 + 86400)}
    assert burn_rate_per_day(newer, older) == 22500000000.0


def test_burn_rate_refuses_garbage():
    assert burn_rate_per_day({}, {}) is None
    assert burn_rate_per_day(
        {"burned_total": "5", "timestamp": "10"},
        {"burned_total": "5", "timestamp": "10"}) is None
    # non-monotonic (counter reset / bad data) must not produce a rate
    assert burn_rate_per_day(
        {"burned_total": "4", "timestamp": "20"},
        {"burned_total": "9", "timestamp": "10"}) is None


def test_burn_rate_needs_positive_window():
    assert burn_rate_per_day(
        {"burned_total": "9", "timestamp": "10"},
        {"burned_total": "5", "timestamp": "20"}) is None
