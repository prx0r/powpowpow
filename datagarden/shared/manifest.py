"""
DataGarden — Daily Merkle Manifest

At the end of each day, generate a manifest:
- raw object count
- normalized row count
- source count
- Merkle root of all immutable observations

Publish/sign independently. Prove September 2026 dataset existed in September 2026.

Uses SHA-256 Merkle tree. Can optionally integrate with OpenTimestamps
for Bitcoin-backed existence proofs.
"""

import hashlib
import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional

MANIFEST_DIR = Path(__file__).parent.parent / 'canonical' / 'manifests'
WAREHOUSE_DIR = Path(__file__).parent.parent / 'canonical'


def _hash_file(filepath: str) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _merkle_root(hashes: List[str]) -> str:
    """Compute Merkle root from a list of leaf hashes."""
    if not hashes:
        return hashlib.sha256(b'empty').hexdigest()

    current = hashes[:]
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            combined = hashlib.sha256(
                (left + right).encode()
            ).hexdigest()
            next_level.append(combined)
        current = next_level

    return current[0]


def count_warehouse_objects() -> Dict[str, int]:
    """Count all objects in the warehouse by category."""
    counts = {
        'raw_files': 0,
        'raw_bytes': 0,
        'jsonl_files': 0,
        'jsonl_rows': 0,
        'jsonl_bytes': 0,
        'by_layer': {},
    }

    for root, dirs, files in os.walk(WAREHOUSE_DIR):
        # Skip manifests and __pycache__
        if 'manifests' in root or '__pycache__' in root:
            continue

        layer = 'unknown'
        rel = os.path.relpath(root, WAREHOUSE_DIR)
        if rel.startswith('canonical_backfill'):
            layer = 'canonical_backfill'
        elif rel.startswith('ephemeral_archive'):
            layer = 'ephemeral_archive'
        elif rel.startswith('knowledge'):
            layer = 'knowledge'
        elif rel.startswith('derived'):
            layer = 'derived'

        if layer not in counts['by_layer']:
            counts['by_layer'][layer] = {'files': 0, 'rows': 0, 'bytes': 0}

        for f in files:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue

            if f.endswith('.json'):
                counts['raw_files'] += 1
                counts['raw_bytes'] += size
                counts['by_layer'][layer]['files'] += 1
                counts['by_layer'][layer]['bytes'] += size
            elif f.endswith('.jsonl'):
                counts['jsonl_files'] += 1
                counts['jsonl_bytes'] += size
                counts['by_layer'][layer]['files'] += 1
                counts['by_layer'][layer]['bytes'] += size
                try:
                    with open(fp) as fh:
                        rows = sum(1 for line in fh if line.strip())
                    counts['jsonl_rows'] += rows
                    counts['by_layer'][layer]['rows'] += rows
                except Exception:
                    pass

    return counts


def count_sources() -> int:
    """Count distinct data sources referenced in the warehouse."""
    sources = set()
    for root, dirs, files in os.walk(WAREHOUSE_DIR):
        if 'manifests' in root or '__pycache__' in root:
            continue
        for f in files:
            if f.endswith('.json'):
                try:
                    with open(os.path.join(root, f)) as fh:
                        data = json.load(fh)
                        if isinstance(data, dict):
                            sid = data.get('source_id')
                            if sid:
                                sources.add(sid)
                except Exception:
                    pass
    return len(sources)


def generate_manifest(manifest_date: str = None) -> Dict:
    """
    Generate daily Merkle manifest.

    Returns manifest dict with:
    - date
    - raw object count
    - normalized row count
    - source count
    - Merkle root
    - layer breakdowns
    """
    if manifest_date is None:
        manifest_date = date.today().isoformat()

    os.makedirs(MANIFEST_DIR, exist_ok=True)

    # Collect all file hashes for Merkle tree
    file_hashes = []
    total_files = 0

    for root, dirs, files in os.walk(WAREHOUSE_DIR):
        if 'manifests' in root or '__pycache__' in root:
            continue
        for f in sorted(files):
            if f.endswith(('.json', '.jsonl')):
                fp = os.path.join(root, f)
                try:
                    file_hash = _hash_file(fp)
                    file_hashes.append(file_hash)
                    total_files += 1
                except Exception:
                    pass

    root_hash = _merkle_root(file_hashes)

    counts = count_warehouse_objects()
    n_sources = count_sources()

    manifest = {
        'manifest_date': manifest_date,
        'generated_at': datetime.now().isoformat(),
        'raw_objects': counts['raw_files'],
        'raw_bytes': counts['raw_bytes'],
        'normalized_rows': counts['jsonl_rows'],
        'normalized_files': counts['jsonl_files'],
        'normalized_bytes': counts['jsonl_bytes'],
        'sources': n_sources,
        'files_hashed': total_files,
        'merkle_root': root_hash,
        'schema_version': '2.0',
        'layer_breakdown': counts['by_layer'],
    }

    filepath = os.path.join(MANIFEST_DIR, f"{manifest_date}.json")
    with open(filepath, 'w') as f:
        json.dump(manifest, f, indent=2, default=str)

    return manifest


def get_manifest(manifest_date: str) -> Optional[Dict]:
    """Load a manifest by date."""
    filepath = os.path.join(MANIFEST_DIR, f"{manifest_date}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def list_manifests() -> List[Dict]:
    """List all manifests."""
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    results = []
    for fname in sorted(os.listdir(MANIFEST_DIR)):
        if fname.endswith('.json'):
            with open(os.path.join(MANIFEST_DIR, fname)) as f:
                results.append(json.load(f))
    return results


def verify_manifest_integrity(manifest_date: str) -> bool:
    """Verify that current warehouse state matches a stored manifest.

    Read-only: computes a fresh Merkle root from the warehouse and compares
    it against the stored manifest, without writing anything.
    """
    manifest = get_manifest(manifest_date)
    if not manifest:
        return False

    # Compute current Merkle root (read-only)
    file_hashes = []
    total_files = 0

    for root, dirs, files in os.walk(WAREHOUSE_DIR):
        if 'manifests' in root or '__pycache__' in root:
            continue
        for f in sorted(files):
            if f.endswith(('.json', '.jsonl')):
                fp = os.path.join(root, f)
                try:
                    file_hash = _hash_file(fp)
                    file_hashes.append(file_hash)
                    total_files += 1
                except Exception:
                    pass

    current_root = _merkle_root(file_hashes)
    return current_root == manifest['merkle_root']


if __name__ == '__main__':
    print("Generating daily manifest...")
    manifest = generate_manifest()

    print(f"\n  Date: {manifest['manifest_date']}")
    print(f"  Raw objects: {manifest['raw_objects']:,}")
    print(f"  Raw bytes: {manifest['raw_bytes']:,}")
    print(f"  Normalized rows: {manifest['normalized_rows']:,}")
    print(f"  Normalized files: {manifest['normalized_files']:,}")
    print(f"  Sources: {manifest['sources']}")
    print(f"  Files hashed: {manifest['files_hashed']:,}")
    print(f"  Merkle root: {manifest['merkle_root'][:16]}...")
    print(f"  Schema version: {manifest['schema_version']}")

    print("\n  Layer breakdown:")
    for layer, stats in manifest['layer_breakdown'].items():
        print(f"    {layer:25} files={stats['files']:6,}  rows={stats['rows']:8,}  bytes={stats['bytes']:12,}")
