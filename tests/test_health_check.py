import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import health_check


def write(root, relative, payload):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        json.dump(payload, handle)


def test_health_check_passes_with_fresh_files(tmp_path):
    now = time.time()
    fresh_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    write(
        tmp_path, "warehouse/safetrade_l2_heartbeat.json", {"heartbeat_at": fresh_iso}
    )
    write(tmp_path, "warehouse/chain_state_heartbeat.json", {"heartbeat_at": fresh_iso})
    write(tmp_path, "warehouse/qubic_epoch_state.json", {"ts": now})
    write(tmp_path, "chains/network_state.json", {"QUBIC": {}})
    write(tmp_path, "warehouse/xmr_analytics.json", {"computed_at": fresh_iso})
    write(tmp_path, "warehouse/qubic_analytics.json", {"computed_at": fresh_iso})
    write(tmp_path, "warehouse/btc_context.json", {"computed_at": fresh_iso})

    assert health_check.main(str(tmp_path)) == 0


def test_health_check_fails_with_missing_and_stale_files(tmp_path, capsys):
    old_iso = "2026-09-20T00:00:00Z"
    write(tmp_path, "warehouse/safetrade_l2_heartbeat.json", {"heartbeat_at": old_iso})

    assert health_check.main(str(tmp_path)) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert len(output["failures"]) == len(health_check.CHECKS)
