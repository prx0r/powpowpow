import glob
import json
import os
import shutil
import time
from datetime import UTC, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R2_STATE = os.path.expanduser("~/.local/state/powpowpow/r2-sync.json")

CHECKS = [
    ("safetrade", "warehouse/safetrade_l2_heartbeat.json", "heartbeat_at", 300),
    ("chain_state", "warehouse/chain_state_heartbeat.json", "heartbeat_at", 900),
    ("depth_snapshots", "warehouse/depth_snapshots_heartbeat.json",
     "heartbeat_at", 900),
    ("qubic_epoch", "warehouse/qubic_epoch_state.json", "ts", 3600),
    ("qubic_stats", "warehouse/qubic_stats_heartbeat.json", "heartbeat_at", 900),
    ("qubic_holdings", "warehouse/qubic_holdings_heartbeat.json", "heartbeat_at", 900),
    ("qubic_transfers", "warehouse/qubic_transfers_heartbeat.json", "heartbeat_at", 900),
    ("network_state", "chains/network_state.json", None, 900),
    (
        "daily_state",
        "warehouse/normalized/daily_state/chain=*/date=*/hour=*.jsonl",
        "observed_at",
        4500,
    ),
    (
        "derived_signals",
        "warehouse/normalized/derived_signal/chain=*/date=*/hour=*.jsonl",
        "observed_at",
        4500,
    ),
    ("factors", "chains/factors/cross_chain_factors.json", "timestamp", 4500),
    ("insights", "warehouse/insights.json", "generated_at", 4500),
    (
        "computor_snapshot",
        "warehouse/normalized/computor_snapshot/chain=qubic/date=*/hour=*.jsonl",
        "observed_at",
        5400,
    ),
    ("pipeline_status", "warehouse/powpowpow_heartbeat.json", "heartbeat_at", 900),
    ("r2_sync", "@r2_state", None, 10800),
    ("xmr_analytics", "warehouse/xmr_analytics.json", "computed_at", 43200),
    ("qubic_analytics", "warehouse/qubic_analytics.json", "computed_at", 43200),
    ("btc_context", "warehouse/btc_context.json", "computed_at", 43200),
]


def parse_time(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    return None


def _resolve(root, relative):
    if relative == "@r2_state":
        return R2_STATE if os.path.exists(R2_STATE) else None
    if "*" in relative:
        matches = glob.glob(os.path.join(root, relative))
        if not matches:
            return None
        return max(matches, key=os.path.getmtime)
    path = relative if os.path.isabs(relative) else os.path.join(root, relative)
    return path if os.path.exists(path) else None


def _read_stamp(path, field):
    if field is None:
        return os.path.getmtime(path)
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
            payload = json.loads(last)
        except ValueError:
            return None
        return parse_time(payload.get(field))
    try:
        with open(path) as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    direct = parse_time(payload.get(field)) if isinstance(payload, dict) else None
    if direct is not None:
        return direct
    if isinstance(payload, dict):
        found = [
            parse_time(v.get(field)) for v in payload.values() if isinstance(v, dict)
        ]
        found = [value for value in found if value is not None]
        if found:
            return max(found)
    return None


def check_file(root, relative, field, max_age_seconds, now):
    path = _resolve(root, relative)
    if path is None:
        return f"{relative} missing"
    stamp = _read_stamp(path, field)
    if stamp is None:
        return f"{relative} has no usable {field}"
    if now - stamp > max_age_seconds:
        return f"{relative} stale by {int(now - stamp)}s"
    return None


def check_disk(root, floor=None):
    """Refuse when free space falls below the collectors' pause floor.

    Collectors already stop at POW_MIN_FREE_BYTES; without this check the
    dashboard stays green while nothing is being written.
    """
    if floor is None:
        floor = int(os.environ.get("POW_MIN_FREE_BYTES", str(2 * 1024 ** 3)))
    try:
        free = shutil.disk_usage(root).free
    except OSError as exc:
        return f"cannot stat filesystem: {exc}"
    if free < floor:
        return (f"free {free / 1024 ** 3:.2f} GiB below floor "
                f"{floor / 1024 ** 3:.2f} GiB — collectors paused")
    return None


FAILING_PIPELINE_STATES = {"error", "stale", "unknown", "not_installed"}


def check_pipeline(root):
    """Surface any source powops reported as not-ok.

    `pipeline_status` exits non-zero, but its caller ignores that exit code
    so health_check can run anyway — so the heartbeat is the channel these
    failures must travel on. Without this, an OOM-killed R2 run still shows
    `{"ok": true}`.
    """
    path = os.path.join(root, "warehouse", "powpowpow_heartbeat.json")
    try:
        with open(path) as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    results = payload.get("results") or {}
    if not results:
        return []
    return [
        {"check": f"pipeline:{name}", "failure": f"pipeline reports {status}"}
        for name, status in sorted(results.items())
        if status in FAILING_PIPELINE_STATES
    ]


def main(root=BASE_DIR):
    now = time.time()
    failures = []
    for name, relative, field, max_age in CHECKS:
        failure = check_file(root, relative, field, max_age, now)
        if failure:
            failures.append({"check": name, "failure": failure})
    failures.extend(check_pipeline(root))
    disk_failure = check_disk(root)
    if disk_failure:
        failures.append({"check": "disk", "failure": disk_failure})
    print(json.dumps({"ok": not failures, "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
