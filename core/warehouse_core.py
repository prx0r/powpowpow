"""
PowPowPow Core — Domain-Agnostic Warehouse

Shared storage for resource/constraint observations across all verticals.
Every domain (PoW, GPU cloud, semiconductors, energy) writes here.
Cross-layer Seesaws emerge from the joins.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

CORE_DIR = '/home/box/powpowpow/core/warehouse'

SUBDIRS = [
    'resources',
    'suppliers',
    'capacity',
    'prices',
    'lead_times',
    'inventory',
    'demand_events',
    'constraint_events',
    'constraint_state',
    'cross_layer',
    'regions',
    'methodology',
]


def _ensure_dirs():
    for subdir in SUBDIRS:
        os.makedirs(os.path.join(CORE_DIR, subdir), exist_ok=True)

_ensure_dirs()


def store_observation(subdir: str, data: dict, partition_key: str = None) -> str:
    """
    Store a core observation.

    Args:
        subdir: One of SUBDIRS
        data: Observation dict
        partition_key: Optional partition (e.g., resource_id)
    """
    base = os.path.join(CORE_DIR, subdir)
    if partition_key:
        base = os.path.join(base, partition_key)
    os.makedirs(base, exist_ok=True)

    ts = datetime.now()
    date_dir = os.path.join(base, f"date={ts:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)

    filepath = os.path.join(date_dir, f"hour={ts:%H}.jsonl")

    record = {
        'timestamp': ts.isoformat(),
        **data,
    }

    with open(filepath, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')

    return filepath


def read_observations(subdir: str, partition_key: str = None,
                      date: str = None) -> List[dict]:
    """Read core observations."""
    base = os.path.join(CORE_DIR, subdir)
    if partition_key:
        base = os.path.join(base, partition_key)

    if not os.path.exists(base):
        return []

    results = []
    for root, dirs, files in os.walk(base):
        if date and f"date={date}" not in root:
            continue
        for f in sorted(files):
            if f.endswith('.jsonl'):
                with open(os.path.join(root, f)) as fh:
                    for line in fh:
                        if line.strip():
                            results.append(json.loads(line))
    return results


def query_resource_history(resource_id: str, subdir: str,
                           start_date: str = None,
                           end_date: str = None) -> List[dict]:
    """Query time-series for a resource in a given subdir."""
    return read_observations(subdir, partition_key=resource_id)


def get_latest_observation(subdir: str, partition_key: str = None) -> Optional[dict]:
    """Get the most recent observation."""
    obs = read_observations(subdir, partition_key)
    if not obs:
        return None
    return obs[-1]


if __name__ == '__main__':
    print("Core warehouse directories:")
    for subdir in SUBDIRS:
        print(f"  {subdir}/")

    # Test store
    path = store_observation('prices', {
        'resource_id': 'gpu_hour_h100',
        'price': 2.50,
        'venue': 'akash',
    }, partition_key='gpu_hour_h100')
    print(f"\nStored: {path}")

    # Test read
    obs = read_observations('prices', partition_key='gpu_hour_h100')
    print(f"Read: {len(obs)} observations")
