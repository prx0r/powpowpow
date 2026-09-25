import json
import os
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import health_check


def write(path, payload, lines=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if lines is not None:
        target.write_text("\n".join(json.dumps(row) for row in lines) + "\n")
    else:
        target.write_text(json.dumps(payload))


def fresh(tmp_path):
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    now = time.time()
    write(tmp_path / "warehouse/safetrade_l2_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/chain_state_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/qubic_epoch_state.json", {"ts": now})
    write(tmp_path / "warehouse/qubic_stats_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/qubic_holdings_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/qubic_transfers_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "chains/network_state.json", {"QUBIC": {}})
    write(tmp_path / "warehouse/powpowpow_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/insights.json", {"generated_at": iso})
    write(tmp_path / "warehouse/xmr_analytics.json", {"computed_at": iso})
    write(tmp_path / "warehouse/qubic_analytics.json", {"computed_at": iso})
    write(tmp_path / "warehouse/btc_context.json", {"computed_at": iso})
    write(
        tmp_path / "chains/factors/cross_chain_factors.json",
        {"BTC": {"timestamp": iso}},
    )
    write(
        tmp_path / "warehouse/normalized/daily_state/chain=safetrade"
        "/date=2026-01-01/hour=00.jsonl",
        None,
        lines=[{"observed_at": iso}],
    )
    write(
        tmp_path / "warehouse/normalized/derived_signal/chain=venue"
        "/date=2026-01-01/hour=00.jsonl",
        None,
        lines=[{"observed_at": iso}],
    )
    write(
        tmp_path / "warehouse/normalized/computor_snapshot/chain=qubic"
        "/date=2026-01-01/hour=00.jsonl",
        None,
        lines=[{"observed_at": iso}],
    )
    write(tmp_path / "r2-state.json", {"powpowpow/x": {"verified_at": now}})


def test_health_check_passes_with_fresh_files(tmp_path, monkeypatch, capsys):
    fresh(tmp_path)
    monkeypatch.setattr(health_check, "R2_STATE", str(tmp_path / "r2-state.json"))

    assert health_check.main(str(tmp_path)) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"ok": True, "failures": []}


def test_health_check_fails_with_missing_and_stale_files(tmp_path, monkeypatch, capsys):
    old_iso = "2026-09-20T00:00:00Z"
    write(tmp_path / "warehouse/safetrade_l2_heartbeat.json", {"heartbeat_at": old_iso})
    monkeypatch.setattr(health_check, "R2_STATE", str(tmp_path / "absent.json"))

    assert health_check.main(str(tmp_path)) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert len(output["failures"]) == len(health_check.CHECKS)
    assert {f["check"] for f in output["failures"]} == {
        c[0] for c in health_check.CHECKS
    }


def test_health_check_watches_every_pipeline_output():
    watched = {c[0] for c in health_check.CHECKS}
    assert {
        "safetrade",
        "chain_state",
        "qubic_epoch",
        "network_state",
        "daily_state",
        "derived_signals",
        "factors",
        "computor_snapshot",
        "pipeline_status",
        "r2_sync",
    } <= watched


def test_health_check_fails_when_pipeline_reports_failure(
    tmp_path, monkeypatch, capsys
):
    fresh(tmp_path)
    monkeypatch.setattr(health_check, "R2_STATE", str(tmp_path / "r2-state.json"))
    path = tmp_path / "warehouse" / "powpowpow_heartbeat.json"
    path.write_text(
        json.dumps(
            {
                "heartbeat_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "results": {"r2_sync": "error"},
            }
        )
    )

    assert health_check.main(str(tmp_path)) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert any(f["check"] == "pipeline:r2_sync" for f in output["failures"])
