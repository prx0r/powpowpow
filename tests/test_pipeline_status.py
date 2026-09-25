import json
import os
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pipeline_status


def write(path, payload, lines=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if lines is not None:
        target.write_text("\n".join(json.dumps(row) for row in lines) + "\n")
    else:
        target.write_text(json.dumps(payload))


def build_tree(tmp_path, iso):
    now = time.time()
    write(tmp_path / "warehouse/safetrade_l2_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/chain_state_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/qubic_epoch_state.json", {"ts": now})
    write(tmp_path / "warehouse/qubic_stats_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/xmr_analytics.json", {"computed_at": iso})
    write(tmp_path / "warehouse/powpowpow_heartbeat.json", {"heartbeat_at": iso})
    write(tmp_path / "warehouse/insights.json", {"generated_at": iso})
    write(
        tmp_path / "chains/factors/cross_chain_factors.json",
        {"BTC": {"timestamp": iso}},
    )
    write(
        tmp_path / "warehouse/normalized/daily_state/chain=safetrade"
        "/date=2026-01-01/hour=00.jsonl",
        None,
        lines=[{"observed_at": iso}, {"observed_at": iso}],
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


def test_collect_returns_powops_contract(tmp_path, monkeypatch):
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    build_tree(tmp_path, iso)
    monkeypatch.setattr(pipeline_status, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline_status, "R2_STATE", str(tmp_path / "r2-state.json"))
    monkeypatch.setattr(pipeline_status, "_unit_state", lambda unit: "active")
    monkeypatch.setattr(pipeline_status, "_site_probe", lambda: (200, time.time()))

    payload = pipeline_status.collect(str(tmp_path))

    heartbeat = payload["heartbeat"]
    assert set(heartbeat) >= {
        "heartbeat_at",
        "mode",
        "total_records",
        "sources_run",
        "sources_failed",
        "results",
    }
    assert heartbeat["mode"] == "pipeline_status"
    assert heartbeat["sources_run"] == len(payload["sources"])
    assert heartbeat["sources_failed"] == 0
    assert set(heartbeat["results"]) == {
        "safetrade_l2",
        "chain_state",
        "qubic_epoch",
        "qubic_stats",
        "qubic_computors",
        "daily_state",
        "derived_signals",
        "cross_chain_factors",
        "insights",
        "mining_analytics",
        "r2_sync",
        "pow_site",
    }

    for source in payload["sources"]:
        assert set(source) >= {
            "source_id",
            "started_at",
            "status",
            "error",
            "duration_seconds",
            "source_records_new",
            "raw_new",
        }
        assert source["status"] in {"ok", "stale", "error", "unknown", "not_installed"}


def test_collect_flags_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_status, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline_status, "R2_STATE", str(tmp_path / "absent.json"))
    monkeypatch.setattr(pipeline_status, "_unit_state", lambda unit: "inactive")
    monkeypatch.setattr(pipeline_status, "_site_probe", lambda: (None, None))

    payload = pipeline_status.collect(str(tmp_path))

    assert payload["heartbeat"]["sources_failed"] > 0
    by_id = {s["source_id"]: s for s in payload["sources"]}
    assert by_id["safetrade_l2"]["status"] in ("not_installed", "unknown")
    assert by_id["pow_site"]["status"] == "error"


def test_write_artifacts_emits_heartbeat_and_run(tmp_path, monkeypatch):
    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    build_tree(tmp_path, iso)
    monkeypatch.setattr(pipeline_status, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(
        pipeline_status,
        "HEARTBEAT_PATH",
        str(tmp_path / "warehouse/powpowpow_heartbeat.json"),
    )
    monkeypatch.setattr(
        pipeline_status, "RUN_PATH", str(tmp_path / "warehouse/collector_run.json")
    )
    monkeypatch.setattr(pipeline_status, "R2_STATE", str(tmp_path / "r2-state.json"))
    monkeypatch.setattr(pipeline_status, "_unit_state", lambda unit: "active")
    monkeypatch.setattr(pipeline_status, "_site_probe", lambda: (200, time.time()))

    payload = pipeline_status.write_artifacts(str(tmp_path))

    heartbeat = json.loads(
        (tmp_path / "warehouse/powpowpow_heartbeat.json").read_text()
    )
    run = json.loads((tmp_path / "warehouse/collector_run.json").read_text())
    assert heartbeat["heartbeat_at"] == payload["heartbeat"]["heartbeat_at"]
    assert isinstance(run, list) and len(run) == len(payload["sources"])
    assert run[0]["source_id"]


def test_freshest_stamp_reads_last_jsonl_line(tmp_path):
    from datetime import UTC, datetime

    path = tmp_path / "hour=00.jsonl"
    path.write_text(
        json.dumps({"observed_at": "2026-09-25T10:00:00Z"})
        + "\n"
        + json.dumps({"observed_at": "2026-09-25T11:30:00Z"})
        + "\n"
    )
    stamp = pipeline_status._freshest_stamp(str(path), "observed_at")
    expected = datetime(2026, 9, 25, 11, 30, tzinfo=UTC).timestamp()
    assert int(stamp) == int(expected)


def test_freshest_stamp_falls_back_to_mtime_when_no_field(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{}")
    stamp = pipeline_status._freshest_stamp(str(path), None)
    assert abs(stamp - path.stat().st_mtime) < 1
