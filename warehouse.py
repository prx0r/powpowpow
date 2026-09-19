"""
PowPowPow — Warehouse Layer

Two-class storage architecture:
  canonical_backfill  — reconstructable truth, backfill when needed
  ephemeral_archive   — time-sensitive truth, archive continuously because time destroys it

Plus knowledge/ for point-in-time entity labels.

Moat foundations (September 2026 genesis):
  - Permanent entity IDs (entities.py)
  - Universe snapshots (universe.py)
  - Bitemporal knowledge with revision tracking
  - Daily Merkle manifests (manifest.py)
  - Source quality history (source_quality.py)
  - Experiment/hypothesis registry (experiments.py)
  - Metric versioning (metrics.py)
  - Forecast snapshots & counterfactuals (counterfactuals.py)
  - Dead system tracking (dead_systems.py)
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

WAREHOUSE_DIR = '/home/box/powpowpow/warehouse'

# --- Directory structure ---

BACKFILL_DIR = os.path.join(WAREHOUSE_DIR, 'canonical_backfill')
EPHEMERAL_DIR = os.path.join(WAREHOUSE_DIR, 'ephemeral_archive')
KNOWLEDGE_DIR = os.path.join(WAREHOUSE_DIR, 'knowledge')
DERIVED_DIR = os.path.join(WAREHOUSE_DIR, 'derived')

# Canonical backfill subdirectories (reconstructable)
BACKFILL_SUBDIRS = {
    'blockchain': ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm', 'npt', 'qtc', 'kas'],
    'price': ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm', 'npt', 'qtc', 'kas'],
    'electricity': ['us_grid', 'eu_grid'],
    'gpu_price': ['daily_median', 'provider_history'],
}

# Ephemeral archive subdirectories (P0 — start clock NOW)
EPHEMERAL_SUBDIRS = {
    'exchange_l2': ['safetrade', 'gate', 'coinex'],
    'pool_state': ['prl', 'xmr', 'qubic', 'kas'],
    'stratum': ['prl', 'xmr'],
    'compute_marketplaces': ['akash', 'clore', 'nosana'],
    'gpu_availability': ['gpufinder', 'gpus_io', 'ssp'],
    'hardware_market': ['asic_miner_value', 'ssp_inventory'],
    'probes': ['pearl_stratum', 'qubic_rpc', 'akash_latency', 'exchange_arrival'],
}

# Knowledge subdirectories
KNOWLEDGE_SUBDIRS = {
    'entities': ['addresses', 'wallets', 'pools'],
    'labels': ['pool_labels', 'exchange_labels', 'miner_labels'],
    'protocol_events': ['releases', 'parameter_changes', 'hard_forks'],
}

# Derived subdirectories
DERIVED_SUBDIRS = {
    'seesaw_state': ['margin', 'wedge', 'absorption', 'pressure'],
    'factors': ['daily', 'hourly'],
    'backtests': ['h1', 'h2', 'h3', 'h4', 'h5', 'experiments'],
}


def _create_dirs():
    """Create all warehouse directories."""
    for base, subdirs in [
        (BACKFILL_DIR, BACKFILL_SUBDIRS),
        (EPHEMERAL_DIR, EPHEMERAL_SUBDIRS),
        (KNOWLEDGE_DIR, KNOWLEDGE_SUBDIRS),
        (DERIVED_DIR, DERIVED_SUBDIRS),
    ]:
        os.makedirs(base, exist_ok=True)
        for group, items in subdirs.items():
            for item in items:
                os.makedirs(os.path.join(base, group, item), exist_ok=True)

_create_dirs()


# --- Recoverability classification ---

RECOVERABILITY = {
    # Canonical backfill (reconstructable)
    'block': 'canonical_reconstructable',
    'difficulty': 'canonical_reconstructable',
    'emission': 'canonical_reconstructable',
    'xmr_hashrate': 'canonical_reconstructable',
    'ohlcv': 'canonical_reconstructable',
    'electricity': 'canonical_reconstructable',
    'gpu_price_daily': 'canonical_reconstructable',
    'protocol_release': 'canonical_reconstructable',

    # Partially reconstructable
    'prl_pool_share': 'partially_reconstructable',
    'prl_transfer': 'partially_reconstructable',
    'individual_trade': 'partially_reconstructable',

    # Third-party reconstructable
    'miner_labels': 'third_party_reconstructable',
    'exchange_labels': 'third_party_reconstructable',

    # Ephemeral (P0 — cannot reconstruct later)
    'exchange_l2': 'ephemeral',
    'pool_worker_count': 'ephemeral',
    'pool_reported_hashrate': 'ephemeral',
    'stratum_job': 'ephemeral',
    'akash_gpu_availability': 'ephemeral',
    'clore_marketplace': 'ephemeral',
    'clore_spot_bids': 'ephemeral',
    'nosana_host_state': 'ephemeral',
    'gpu_stockout': 'ephemeral',
    'hardware_listing': 'ephemeral',
    'probe_latency': 'ephemeral',
}


# --- Core storage functions ---

def store_raw_event(chain: str, event_type: str, payload: dict,
                    source_info: Optional[dict] = None,
                    recoverability: str = 'unknown') -> str:
    """
    Store raw event immutably with bitemporal metadata.

    Args:
        chain: Chain identifier (qubic, prl, xmr, etc.)
        event_type: Type of event (tick, block, trade, depth, etc.)
        payload: Raw data payload (dict or list)
        source_info: Optional dict with source metadata
        recoverability: One of RECOVERABILITY values
    """
    timestamp = datetime.now().isoformat()

    observation = {
        'observed_at': timestamp,
        'chain_id': chain,
        'event_type': event_type,
        'recoverability': recoverability,
        'source_id': source_info.get('source_id', 'unknown') if source_info else 'unknown',
        'source_type': source_info.get('source_type', 'unknown') if source_info else 'unknown',
        'source_version': source_info.get('source_version', '1.0') if source_info else '1.0',
        'endpoint': source_info.get('endpoint', '') if source_info else '',
        'request_params': source_info.get('params', {}) if source_info else {},
        'raw_payload': payload,
        'payload_hash': hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest(),
        'ingest_version': '2.0',
    }

    # Route to correct directory based on recoverability
    if recoverability in ('ephemeral',):
        base_dir = os.path.join(EPHEMERAL_DIR, 'raw', chain)
    elif recoverability in ('canonical_reconstructable', 'third_party_reconstructable'):
        base_dir = os.path.join(BACKFILL_DIR, 'raw', chain)
    else:
        base_dir = os.path.join(BACKFILL_DIR, 'raw', chain)

    os.makedirs(base_dir, exist_ok=True)

    filename = f"{event_type}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    filepath = os.path.join(base_dir, filename)

    with open(filepath, 'w') as f:
        json.dump(observation, f, indent=2, default=str)

    return filepath


def store_normalized(table_name: str, chain: str, data: dict,
                     timestamp: Optional[datetime] = None,
                     recoverability: str = 'unknown') -> str:
    """
    Store normalized data in partitioned tables with recoverability metadata.
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Route to correct base directory
    if recoverability == 'ephemeral':
        base = EPHEMERAL_DIR
    else:
        base = BACKFILL_DIR

    table_dir = os.path.join(base, 'normalized', table_name)
    os.makedirs(table_dir, exist_ok=True)

    date_dir = os.path.join(table_dir, f"chain={chain}", f"date={timestamp:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)

    hour_file = os.path.join(date_dir, f"hour={timestamp:%H}.jsonl")

    record = {
        'timestamp': timestamp.isoformat(),
        'chain': chain,
        'recoverability': recoverability,
        **data
    }

    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')

    return hour_file


def store_ephemeral(layer: str, sublayer: str, data: dict,
                    timestamp: Optional[datetime] = None) -> str:
    """
    Store ephemeral (P0) data. These are observations that cannot be
    reconstructed later and must be archived continuously.
    """
    if timestamp is None:
        timestamp = datetime.now()

    layer_dir = os.path.join(EPHEMERAL_DIR, layer, sublayer)
    os.makedirs(layer_dir, exist_ok=True)

    date_dir = os.path.join(layer_dir, f"date={timestamp:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)

    hour_file = os.path.join(date_dir, f"hour={timestamp:%H}.jsonl")

    record = {
        'timestamp': timestamp.isoformat(),
        'recoverability': 'ephemeral',
        **data
    }

    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')

    return hour_file


def store_knowledge(category: str, subcategory: str, entity_id: str,
                    label: str, known_at: Optional[datetime] = None,
                    valid_from: Optional[str] = None) -> str:
    """
    Store point-in-time entity knowledge.

    Even if the underlying blockchain is public, our *knowledge* of entity
    identities at time T is proprietary. Preserve valid_from/known_at to
    prevent lookahead bias in backtests.
    """
    if known_at is None:
        known_at = datetime.now()

    dir_path = os.path.join(KNOWLEDGE_DIR, category, subcategory)
    os.makedirs(dir_path, exist_ok=True)

    filepath = os.path.join(dir_path, f"{entity_id}.json")

    # Load existing or create new
    if os.path.exists(filepath):
        with open(filepath) as f:
            record = json.load(f)
    else:
        record = {
            'entity_id': entity_id,
            'category': category,
            'subcategory': subcategory,
            'history': [],
        }

    # Append new knowledge observation
    record['history'].append({
        'label': label,
        'known_at': known_at.isoformat(),
        'valid_from': valid_from or known_at.isoformat(),
    })

    # Update current label
    record['current_label'] = label
    record['last_updated'] = known_at.isoformat()

    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return filepath


def store_derived(table_name: str, subcategory: str, data: dict,
                  timestamp: Optional[datetime] = None) -> str:
    """Store derived/computed data (seesaw state, factors, backtest results)."""
    if timestamp is None:
        timestamp = datetime.now()

    table_dir = os.path.join(DERIVED_DIR, table_name, subcategory)
    os.makedirs(table_dir, exist_ok=True)

    date_dir = os.path.join(table_dir, f"date={timestamp:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)

    hour_file = os.path.join(date_dir, f"hour={timestamp:%H}.jsonl")

    record = {
        'timestamp': timestamp.isoformat(),
        **data
    }

    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')

    return hour_file


# --- Read functions ---

def read_ephemeral(layer: str, sublayer: str = None, date: str = None) -> list:
    """Read ephemeral archive data."""
    if sublayer:
        base = os.path.join(EPHEMERAL_DIR, layer, sublayer)
    else:
        base = os.path.join(EPHEMERAL_DIR, layer)

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


def read_knowledge(category: str, subcategory: str,
                   entity_id: Optional[str] = None,
                   as_of: Optional[str] = None) -> list:
    """
    Read point-in-time knowledge.

    If as_of is provided, return only labels that were known at that time.
    """
    dir_path = os.path.join(KNOWLEDGE_DIR, category, subcategory)
    if not os.path.exists(dir_path):
        return []

    results = []

    if entity_id:
        files = [f"{entity_id}.json"]
    else:
        files = [f for f in os.listdir(dir_path) if f.endswith('.json')]

    for fname in files:
        fpath = os.path.join(dir_path, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            record = json.load(f)

        if as_of:
            # Filter history to only observations known at as_of time
            record['history'] = [
                h for h in record['history']
                if h['known_at'] <= as_of
            ]
            if record['history']:
                record['current_label'] = record['history'][-1]['label']
            else:
                continue

        results.append(record)

    return results


def read_normalized(table_name: str, chain: str = None, date: str = None,
                    base: str = None) -> list:
    """Read normalized data from table."""
    if base is None:
        base = BACKFILL_DIR

    table_dir = os.path.join(base, 'normalized', table_name)
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


def read_derived(table_name: str, subcategory: str = None, date: str = None) -> list:
    """Read derived data."""
    if subcategory:
        base = os.path.join(DERIVED_DIR, table_name, subcategory)
    else:
        base = os.path.join(DERIVED_DIR, table_name)

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


# --- Legacy compatibility ---

# Keep old API working
RAW_DIR = os.path.join(WAREHOUSE_DIR, 'raw')
NORMALIZED_DIR = os.path.join(WAREHOUSE_DIR, 'normalized')

for d in [RAW_DIR, NORMALIZED_DIR]:
    os.makedirs(d, exist_ok=True)
    for subdir in ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm', 'npt', 'qtc', 'market']:
        os.makedirs(os.path.join(d, subdir), exist_ok=True)


def store_infrastructure(layer, data, timestamp=None):
    """Legacy: store infrastructure-layer data."""
    return store_ephemal(layer, 'default', data, timestamp)


def read_infrastructure(layer, date=None):
    """Legacy: read infrastructure-layer data."""
    return read_ephemeral(layer, date=date)


if __name__ == '__main__':
    print("Testing warehouse v2...\n")

    # Test ephemeral storage
    print("1. Ephemeral storage (exchange L2)...")
    path = store_ephemeral('exchange_l2', 'safetrade', {
        'symbol': 'PRL',
        'bids': [[100.0, 500.0], [99.5, 1000.0]],
        'asks': [[100.5, 300.0], [101.0, 800.0]],
    })
    print(f"   Stored: {path}")

    # Test knowledge storage
    print("\n2. Knowledge storage (entity labels)...")
    path = store_knowledge('entities', 'wallets', '0xabc123', 'safetrade_exchange',
                           valid_from='2026-09-01')
    print(f"   Stored: {path}")

    # Test point-in-time read
    print("\n3. Point-in-time knowledge read...")
    records = read_knowledge('entities', 'wallets', as_of='2026-09-15')
    print(f"   Found {len(records)} entities known by 2026-09-15")

    # Test derived storage
    print("\n4. Derived storage (seesaw state)...")
    path = store_derived('seesaw_state', 'margin', {
        'symbol': 'PRL',
        'mining_margin': 0.045,
        'wedge': 0.023,
    })
    print(f"   Stored: {path}")

    # Show directory structure
    print("\n5. Warehouse structure:")
    for root, dirs, files in os.walk(WAREHOUSE_DIR):
        level = root.replace(WAREHOUSE_DIR, '').count(os.sep)
        indent = '  ' * level
        basename = os.path.basename(root)
        if level <= 2:
            print(f"   {indent}{basename}/")

    print("\nDone!")
