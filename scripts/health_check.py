import json
import os
import time
from datetime import UTC, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    ("safetrade", "warehouse/safetrade_l2_heartbeat.json", "heartbeat_at", 300),
    ("chain_state", "warehouse/chain_state_heartbeat.json", "heartbeat_at", 900),
    ("qubic_epoch", "warehouse/qubic_epoch_state.json", "ts", 3600),
    ("network_state", "chains/network_state.json", None, 900),
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


def check_file(root, relative, field, max_age_seconds, now):
    path = os.path.join(root, relative)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return f"{relative} missing"
    stamp = mtime
    if field:
        try:
            with open(path) as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return f"{relative} unreadable"
        parsed = parse_time(payload.get(field))
        if parsed is None:
            return f"{relative} has no usable {field}"
        stamp = parsed
    if now - stamp > max_age_seconds:
        return f"{relative} stale by {int(now - stamp)}s"
    return None


def main(root=BASE_DIR):
    now = time.time()
    failures = []
    for name, relative, field, max_age in CHECKS:
        failure = check_file(root, relative, field, max_age, now)
        if failure:
            failures.append({"check": name, "failure": failure})
    print(json.dumps({"ok": not failures, "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
