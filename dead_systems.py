"""
PowPowPow — Dead System Tracker

Track dead networks, pools, exchanges, providers.
Failures let you study: what does resource-market death look like before it happens?

Competitors starting in 2029 won't be able to collect the dead 2026 projects.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

DEAD_DIR = '/home/box/powpowpow/warehouse/knowledge/dead_systems'


def _ensure_dir():
    os.makedirs(DEAD_DIR, exist_ok=True)


def record_death(
    entity_id: str,
    category: str,
    name: str,
    last_seen: str,
    last_price: Optional[float] = None,
    last_hashrate: Optional[float] = None,
    last_capacity: Optional[int] = None,
    shutdown_event: Optional[str] = None,
    failure_reason: Optional[str] = None,
    symptoms_before_death: Optional[List[str]] = None,
    days_before_death: Optional[int] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Record a system death with pre-mortem symptoms.
    """
    _ensure_dir()

    record = {
        'entity_id': entity_id,
        'category': category,
        'name': name,
        'last_seen': last_seen,
        'recorded_at': datetime.now().isoformat(),
        'last_price': last_price,
        'last_hashrate': last_hashrate,
        'last_capacity': last_capacity,
        'shutdown_event': shutdown_event,
        'failure_reason': failure_reason,
        'symptoms_before_death': symptoms_before_death or [],
        'days_before_death': days_before_death,
        'metadata': metadata or {},
    }

    filepath = os.path.join(DEAD_DIR, f"{entity_id}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return record


def get_dead_system(entity_id: str) -> Optional[Dict]:
    """Get death record for an entity."""
    filepath = os.path.join(DEAD_DIR, f"{entity_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def list_dead_systems(category: Optional[str] = None) -> List[Dict]:
    """List all dead systems with optional category filter."""
    _ensure_dir()
    results = []
    for fname in sorted(os.listdir(DEAD_DIR)):
        if fname.endswith('.json'):
            with open(os.path.join(DEAD_DIR, fname)) as f:
                record = json.load(f)
            if category and record.get('category') != category:
                continue
            results.append(record)
    return results


def get_death_symptoms() -> Dict[str, List[str]]:
    """Aggregate common symptoms across all deaths (for pattern detection)."""
    all_symptoms = {}
    for record in list_dead_systems():
        for symptom in record.get('symptoms_before_death', []):
            if symptom not in all_symptoms:
                all_symptoms[symptom] = []
            all_symptoms[symptom].append(record['entity_id'])
    return all_symptoms


if __name__ == '__main__':
    # Example deaths
    record_death(
        entity_id='pool-dead-example',
        category='pool',
        name='DeadPool',
        last_seen='2026-08-15',
        last_hashrate=500000,
        shutdown_event='pool operator exit',
        failure_reason='operator abandoned project',
        symptoms_before_death=[
            'declining hashrate 30d',
            'increased payout delays',
            'pool fee increased',
            'website down 48h before',
        ],
        days_before_death=45,
    )
    print("Recorded death: pool-dead-example")

    deaths = list_dead_systems()
    print(f"\nDead systems tracked: {len(deaths)}")

    symptoms = get_death_symptoms()
    print("\nCommon pre-mortem symptoms:")
    for symptom, entities in symptoms.items():
        print(f"  {symptom}: {len(entities)} occurrences")
