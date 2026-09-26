"""Tests for burn_ledger helpers — pure logic, no network."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.burn_ledger import parse_event


def _ev(**kw):
    base = {"epoch": 232, "tickNumber": 81788144, "timestamp": "1790438764000",
            "logType": 8, "logId": "4709132", "transactionHash": "abc",
            "categories": [4],
            "burning": {"source": "NAAAA", "amount": "25069", "contractIndex": "13"}}
    base.update(kw)
    return base


def test_parse_ok():
    r = parse_event(_ev())
    assert r["log_id"] == 4709132
    assert r["amount"] == 25069
    assert r["contract"] == "13"
    assert r["event_time_ms"] == 1790438764000


def test_parse_rejects_garbage():
    assert parse_event(_ev(burning={"amount": "0"})) is None
    assert parse_event(_ev(burning={"amount": "xyz"})) is None
    assert parse_event(_ev(logId="nope")) is None
    assert parse_event(_ev(timestamp="0")) is None
    assert parse_event({}) is None


def test_parse_handles_missing_burning():
    r = parse_event(_ev(burning=None))
    assert r is None
