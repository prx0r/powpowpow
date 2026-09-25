import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from collectors import chain_state, l2_archival


def test_l2_disk_low_respects_threshold(monkeypatch):
    monkeypatch.setattr(l2_archival, "MIN_FREE_BYTES", 0)
    assert l2_archival.L2Archival().disk_low() is False

    monkeypatch.setattr(l2_archival, "MIN_FREE_BYTES", 10**15)
    assert l2_archival.L2Archival().disk_low() is True


def test_chain_state_disk_guard_respects_threshold(monkeypatch):
    monkeypatch.setattr(chain_state, "MIN_FREE_BYTES", 0)
    assert chain_state.require_disk() is True

    monkeypatch.setattr(chain_state, "MIN_FREE_BYTES", 10**15)
    assert chain_state.require_disk() is False


def test_disk_guard_is_enabled_by_default():
    floor = 2 * 1024**3
    assert l2_archival.MIN_FREE_BYTES == floor
    assert chain_state.MIN_FREE_BYTES == floor
