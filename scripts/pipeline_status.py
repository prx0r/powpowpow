import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

HEARTBEAT_PATH = os.path.join(BASE_DIR, "warehouse", "powpowpow_heartbeat.json")
RUN_PATH = os.path.join(BASE_DIR, "warehouse", "collector_run.json")
R2_STATE = os.path.expanduser("~/.local/state/powpowpow/r2-sync.json")

# source_id -> (unit, freshness path, field, max_age_seconds)
SOURCES = (
    (
        "safetrade_l2",
        "pow-safetrade-l2",
        "warehouse/safetrade_l2_heartbeat.json",
        "heartbeat_at",
        300,
    ),
    (
        "chain_state",
        "pow-chain-state",
        "warehouse/chain_state_heartbeat.json",
        "heartbeat_at",
        900,
    ),
    (
        "qubic_epoch",
        "pow-qubic-epoch.timer",
        "warehouse/qubic_epoch_state.json",
        "ts",
        3600,
    ),
    (
        "qubic_stats",
        "pow-qubic-stats",
        "warehouse/qubic_stats_heartbeat.json",
        "heartbeat_at",
        900,
    ),
    (
        "qubic_computors",
        "pow-qubic-computors.timer",
        "warehouse/normalized/computor_snapshot/chain=qubic/date=*/hour=*.jsonl",
        "observed_at",
        5400,
    ),
    (
        "daily_state",
        "pow-daily-state.timer",
        "warehouse/normalized/daily_state/chain=*/date=*/hour=*.jsonl",
        "observed_at",
        4500,
    ),
    (
        "derived_signals",
        "pow-daily-state.timer",
        "warehouse/normalized/derived_signal/chain=*/date=*/hour=*.jsonl",
        "observed_at",
        4500,
    ),
    (
        "cross_chain_factors",
        "pow-daily-state.timer",
        "chains/factors/cross_chain_factors.json",
        "timestamp",
        4500,
    ),
    (
        "insights",
        "pow-daily-state.timer",
        "warehouse/insights.json",
        "generated_at",
        4500,
    ),
    (
        "mining_analytics",
        "pow-mining-analytics.timer",
        "warehouse/xmr_analytics.json",
        "computed_at",
        43200,
    ),
    ("r2_sync", "pow-r2-upload.timer", R2_STATE, None, 10800),
    ("pow_site", "pow-site", None, None, 300),
)


def _newest(path_pattern):
    if "*" in path_pattern:
        matches = glob.glob(os.path.join(BASE_DIR, path_pattern))
        if not matches:
            return None
        return max(matches, key=os.path.getmtime)
    path = (
        path_pattern
        if os.path.isabs(path_pattern)
        else os.path.join(BASE_DIR, path_pattern)
    )
    return path if os.path.exists(path) else None


def _load(path):
    if not path:
        return {}
    try:
        with open(path) as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _freshest_stamp(path, field):
    """Newest timestamp in a file: last JSONL line, or the deepest JSON value."""
    if not path or field is None:
        return os.path.getmtime(path) if path and os.path.exists(path) else None
    if path.endswith(".jsonl"):
        last = None
        try:
            with open(path) as handle:
                for line in handle:
                    if line.strip():
                        last = line
        except OSError:
            return None
        if not last:
            return None
        try:
            return _stamp(json.loads(last), field)
        except ValueError:
            return None
    payload = _load(path)
    direct = _stamp(payload, field)
    if direct is not None:
        return direct
    best = None
    for value in payload.values():
        if isinstance(value, dict):
            found = _stamp(value, field)
            if found is not None and (best is None or found > best):
                best = found
    return best


def _stamp(payload, field):
    if field is None:
        return None
    value = payload.get(field)
    if isinstance(value, (int, float)) and value < 1e12:
        return value
    if isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return None


def _age(stamp):
    if stamp is None:
        return None
    return max(0, int(time.time() - stamp))


def _unit_state(unit):
    import subprocess

    if not unit.endswith((".timer", ".service")):
        unit = unit + ".service"
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _site_probe():
    try:
        import requests

        response = requests.get("http://127.0.0.1:8795/api/health", timeout=10)
        return response.status_code, datetime.now(timezone.utc).timestamp()
    except Exception:
        return None, None


def _row_count(path):
    if not path or "*" not in path:
        return None
    newest = _newest(path)
    if not newest:
        return None
    count = 0
    try:
        with open(newest) as handle:
            for line in handle:
                if line.strip():
                    count += 1
    except OSError:
        return None
    return count


def collect(root=None):
    """PowPowPow pipeline status in the powops collector_run shape."""
    if root:
        global BASE_DIR
        BASE_DIR = root

    sources = []
    for source_id, unit, path, field, max_age in SOURCES:
        if source_id == "pow_site":
            code, stamp = _site_probe()
            age = _age(stamp)
            status = "ok" if code == 200 else "error"
            sources.append(
                {
                    "source_id": source_id,
                    "unit": unit,
                    "unit_state": _unit_state(unit),
                    "started_at": datetime.fromtimestamp(
                        stamp, tz=timezone.utc
                    ).isoformat()
                    if stamp
                    else None,
                    "status": status,
                    "error": None if status == "ok" else f"http {code}",
                    "age_seconds": age,
                    "max_staleness": max_age,
                    "duration_seconds": None,
                    "source_records_new": None,
                    "raw_new": 0,
                }
            )
            continue

        newest = _newest(path)
        stamp = _freshest_stamp(newest, field) if newest else None
        age = _age(stamp)
        unit_state = _unit_state(unit)

        status = "ok"
        error = None
        if newest is None:
            status = (
                "not_installed" if unit_state in ("inactive", "unknown") else "unknown"
            )
            error = "no data file"
        elif age is None:
            status = "unknown"
            error = f"no {field} in {os.path.basename(newest)}"
        elif age > max_age:
            status = "stale"
            error = f"{age}s old, threshold {max_age}s"
        elif not unit.endswith(".timer") and unit_state not in ("active", "running"):
            status = "error"
            error = f"{unit} is {unit_state}"

        sources.append(
            {
                "source_id": source_id,
                "unit": unit,
                "unit_state": unit_state,
                "started_at": datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat()
                if stamp
                else None,
                "status": status,
                "error": error,
                "age_seconds": age,
                "max_staleness": max_age,
                "duration_seconds": None,
                "source_records_new": _row_count(path),
                "raw_new": 0,
            }
        )

    heartbeat = {
        "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "mode": "pipeline_status",
        "total_records": sum(s["source_records_new"] or 0 for s in sources),
        "sources_run": len(sources),
        "sources_failed": sum(
            1
            for s in sources
            if s["status"] in ("error", "stale", "unknown", "not_installed")
        ),
        "results": {s["source_id"]: s["status"] for s in sources},
    }
    return {"heartbeat": heartbeat, "sources": sources}


def write_artifacts(root=None):
    payload = collect(root)
    for path, body in (
        (HEARTBEAT_PATH, payload["heartbeat"]),
        (RUN_PATH, payload["sources"]),
    ):
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        temporary = path + ".tmp"
        with open(temporary, "w") as handle:
            json.dump(body, handle, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    return payload


def main():
    payload = write_artifacts()
    print(json.dumps(payload["heartbeat"], indent=2))
    for source in payload["sources"]:
        print(
            f"  {source['source_id']:22} {source['status']:13} "
            f"age={source['age_seconds']} {source['error'] or ''}"
        )
    failed = [
        s
        for s in payload["sources"]
        if s["status"] in ("error", "stale", "unknown", "not_installed")
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
