"""
PowPowPow — Universe Snapshot System

Prevents survivorship bias by recording what existed and what
was eligible at each point in time.

Every day store:
  observed_at
  network_id / asset_id
  status: eligible | watch | excluded | dead | delisted
  qualification_reason

Serious financial databases retain dead securities explicitly.
Without this, 2030 backtests would only include survivors.
"""

import json
import os
from datetime import datetime, date
from typing import Optional, Dict, List

UNIVERSE_DIR = '/home/box/powpowpow/warehouse/knowledge/universe'


def _ensure_dir():
    os.makedirs(UNIVERSE_DIR, exist_ok=True)


def snapshot_universe(
    entities: List[Dict],
    observed_at: Optional[str] = None,
    override_status: Optional[Dict[str, str]] = None,
) -> str:
    """
    Store a daily universe snapshot.

    Args:
        entities: List of entity dicts from entities.py
        observed_at: ISO timestamp (defaults to now)
        override_status: Dict of entity_id -> status override

    Returns:
        Path to stored snapshot file
    """
    _ensure_dir()
    if observed_at is None:
        observed_at = datetime.now().isoformat()

    snapshot_date = date.today().isoformat()

    entries = []
    for entity in entities:
        eid = entity['entity_id']
        status = 'eligible'
        reason = f"Entity exists with status={entity.get('status', 'active')}"

        if override_status and eid in override_status:
            status = override_status[eid]
            reason = f"Override: {status}"

        if entity.get('status') == 'dead':
            status = 'dead'
            reason = entity.get('metadata', {}).get('failure_reason', 'Marked dead')
        elif entity.get('status') == 'superseded':
            status = 'excluded'
            reason = f"Superseded by {entity.get('superseded_by', '?')}"

        entries.append({
            'entity_id': eid,
            'category': entity.get('category', 'unknown'),
            'current_name': entity.get('current_name', '?'),
            'status': status,
            'qualification_reason': reason,
            'first_seen': entity.get('first_seen'),
            'last_seen': entity.get('last_seen'),
        })

    snapshot = {
        'observed_at': observed_at,
        'snapshot_date': snapshot_date,
        'n_entities': len(entries),
        'n_eligible': sum(1 for e in entries if e['status'] == 'eligible'),
        'n_dead': sum(1 for e in entries if e['status'] == 'dead'),
        'n_excluded': sum(1 for e in entries if e['status'] == 'excluded'),
        'entries': entries,
    }

    filepath = os.path.join(UNIVERSE_DIR, f"universe_{snapshot_date}.json")
    with open(filepath, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)

    return filepath


def get_universe(snapshot_date: str = None) -> Optional[Dict]:
    """Load a universe snapshot by date."""
    _ensure_dir()
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    filepath = os.path.join(UNIVERSE_DIR, f"universe_{snapshot_date}.json")
    if not os.path.exists(filepath):
        return None

    with open(filepath) as f:
        return json.load(f)


def list_universe_dates() -> List[str]:
    """List all available universe snapshot dates."""
    _ensure_dir()
    dates = []
    for f in sorted(os.listdir(UNIVERSE_DIR)):
        if f.startswith('universe_') and f.endswith('.json'):
            d = f.replace('universe_', '').replace('.json', '')
            dates.append(d)
    return dates


def get_eligible(universe: Dict) -> List[Dict]:
    """Get only eligible entities from a snapshot."""
    return [e for e in universe.get('entries', []) if e['status'] == 'eligible']


def get_dead(universe: Dict) -> List[Dict]:
    """Get dead entities from a snapshot (crucial for survivorship-bias-free backtests)."""
    return [e for e in universe.get('entries', []) if e['status'] == 'dead']


if __name__ == '__main__':
    from entities import bootstrap_entities, list_entities

    bootstrap_entities()

    print("Taking universe snapshot...")
    all_entities = list_entities()
    path = snapshot_universe(all_entities)
    print(f"  Stored: {path}")

    snapshot = get_universe()
    print(f"\n  Total: {snapshot['n_entities']}")
    print(f"  Eligible: {snapshot['n_eligible']}")
    print(f"  Dead: {snapshot['n_dead']}")
    print(f"  Excluded: {snapshot['n_excluded']}")

    print("\n  Dead entities (survivorship bias prevention):")
    for e in get_dead(snapshot):
        print(f"    {e['entity_id']:30} {e['current_name']:20} — {e['qualification_reason']}")
