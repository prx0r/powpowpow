"""
PowPowPow — Raw Event Storage Layer (compat shim).

Single source of truth is `core.py` (bitemporal, UTC-only, auto-archiving).
This module preserves the legacy `warehouse.*` import API and delegates.
"""

import json
import os
from datetime import datetime, timezone

import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import (
    BASE_DIR as CORE_BASE_DIR,
    RAW_DIR as CORE_RAW_DIR,
    utcnow,
    canonical_hash,
    store_normalized as core_store_normalized,
    _archive_raw as core_archive_raw,
)

WAREHOUSE_DIR = os.path.join(CORE_BASE_DIR, 'warehouse')
RAW_DIR = CORE_RAW_DIR
NORMALIZED_DIR = os.path.join(CORE_BASE_DIR, 'warehouse', 'normalized')

# Create directories (legacy subdirs kept for compat)
for d in [RAW_DIR, NORMALIZED_DIR]:
    os.makedirs(d, exist_ok=True)
    for subdir in ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm', 'npt', 'qtc', 'market',
                   'kas', 'clore', 'akt', 'nos', 'quan']:
        os.makedirs(os.path.join(d, subdir), exist_ok=True)


def _to_utc_iso(ts=None):
    """Coerce naive datetime/str to UTC ISO. Never assume local time."""
    if ts is None:
        return utcnow(), datetime.now(timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat(), ts
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(), dt
        except Exception:
            pass
    return utcnow(), datetime.now(timezone.utc)


def store_raw_event(chain, event_type, payload, source_info=None):
    """Legacy wrapper — delegates to core._archive_raw with UTC timestamps."""
    observed_at, _ = _to_utc_iso((source_info or {}).get('observed_at') if isinstance(source_info, dict) else None)
    return core_archive_raw(
        chain_id=chain,
        source_id=(source_info or {}).get('source_id', 'unknown') if source_info else 'unknown',
        endpoint=(source_info or {}).get('endpoint', '') if source_info else '',
        event_time=None,  # legacy callers never supply event_time; do not fake it
        observed_at=observed_at,
        response_received=utcnow(),
        http_status=200,
        raw_body=json.dumps(payload, default=str),
        parsed_payload=payload,
        request_params=(source_info or {}).get('params', {}) if source_info else {},
        quality_flags=['legacy_warehouse_shim'],
    )


def store_normalized(table_name, chain, data, timestamp=None):
    """Legacy wrapper — delegates to core.store_normalized (adds lineage)."""
    _, dt = _to_utc_iso(timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp)
    # core.store_normalized partitions by current UTC hour; pass event_time through
    event_time = data.get('event_time') or data.get('timestamp')
    return core_store_normalized(
        table_name=table_name,
        chain_id=chain,
        data={**data, '_legacy_timestamp': dt.isoformat()},
        event_time=event_time,
    )


def read_normalized(table_name, chain=None, date=None):
    """Read normalized data (same layout as core)."""
    table_dir = os.path.join(NORMALIZED_DIR, table_name)
    if not os.path.exists(table_dir):
        return []
    results = []
    if chain:
        chain_dirs = [os.path.join(table_dir, f"chain={chain}")]
    else:
        chain_dirs = [os.path.join(table_dir, d) for d in os.listdir(table_dir) if d.startswith('chain=')]
    for chain_dir in chain_dirs:
        if not os.path.exists(chain_dir):
            continue
        if date:
            date_dirs = [os.path.join(chain_dir, f"date={date}")]
        else:
            date_dirs = [os.path.join(chain_dir, d) for d in os.listdir(chain_dir) if d.startswith('date=')]
        for date_dir in date_dirs:
            if not os.path.exists(date_dir):
                continue
            for hour_file in sorted(os.listdir(date_dir)):
                if hour_file.endswith('.jsonl'):
                    with open(os.path.join(date_dir, hour_file)) as f:
                        for line in f:
                            if line.strip():
                                results.append(json.loads(line))
    return results


if __name__ == '__main__':
    print("Testing raw event storage (via core)...")
    test_payload = {'tick': 12345, 'epoch': 100, 'tx_count': 5}
    filepath = store_raw_event('qubic', 'tick', test_payload, {
        'source_id': 'qubic-rpc',
        'source_type': 'rpc',
        'endpoint': 'https://rpc.qubic.org/v1/tick-info',
    })
    print(f"  Stored raw event: {filepath}")
    print("\nTesting normalized storage...")
    hour_file = store_normalized('chain_snapshot', 'qubic', {'height': 12345, 'epoch': 100})
    print(f"  Stored normalized: {hour_file}")
    data = read_normalized('chain_snapshot', chain='qubic')
    print(f"  Found {len(data)} records")
    print("\nDone!")
