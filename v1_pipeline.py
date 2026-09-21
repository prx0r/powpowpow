"""
PowPowPow V1 Data Pipeline Architecture (compat shim).

Flow:
  Source APIs → Raw Events → Normalized Tables → Live Cards → API/Exports

Single source of truth is `core.py`. This module preserves the legacy
`v1_pipeline.*` API and delegates to core.
"""

import json
import os
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
from warehouse import read_normalized  # same on-disk layout

WAREHOUSE_DIR = os.path.join(CORE_BASE_DIR, 'warehouse')
RAW_DIR = CORE_RAW_DIR
NORMALIZED_DIR = os.path.join(CORE_BASE_DIR, 'warehouse', 'normalized')

# Create directories
for d in [RAW_DIR, NORMALIZED_DIR]:
    os.makedirs(d, exist_ok=True)
    for chain in ['prl', 'qubic', 'quan', 'xmr', 'kas', 'clore', 'akt', 'nos']:
        os.makedirs(os.path.join(d, chain), exist_ok=True)


def store_raw(chain_id, source_id, source_type, endpoint, payload, node_height=None, node_tip_hash=None):
    """Legacy wrapper — delegates to core with canonical hashing + UTC."""
    observed_at = utcnow()
    return core_archive_raw(
        chain_id=chain_id,
        source_id=source_id,
        endpoint=endpoint,
        event_time=None,
        observed_at=observed_at,
        response_received=utcnow(),
        http_status=200,
        raw_body=json.dumps(payload, default=str),
        parsed_payload=payload,
        request_params={},
        quality_flags=['legacy_v1_pipeline_shim', f'source_type={source_type}'],
    )


def store_normalized(table_name, chain_id, data):
    """Legacy wrapper — delegates to core (adds lineage + UTC partitioning)."""
    return core_store_normalized(
        table_name=table_name,
        chain_id=chain_id,
        data=data,
        event_time=data.get('event_time') or data.get('timestamp'),
    )


if __name__ == '__main__':
    print("Testing V1 Pipeline (via core)...")
    filepath = store_raw(
        chain_id='prl',
        source_id='prlscan-api',
        source_type='rest',
        endpoint='https://prlscan.com/api/v1/network',
        payload={'hashrate': '21.9 EH/s', 'difficulty': '19.99M'}
    )
    print(f"  Raw event: {filepath}")
    hour_file = store_normalized('chain_snapshot', 'prl', {
        'height': 100855,
        'hashrate': 21.9e18,
        'difficulty': 19.99e6,
    })
    print(f"  Normalized: {hour_file}")
    data = read_normalized('chain_snapshot', chain='prl')
    print(f"  Records: {len(data)}")
    if data:
        print(f"  Latest keys: {list(data[-1].keys())[:8]}")
    print("\nPipeline test complete!")
