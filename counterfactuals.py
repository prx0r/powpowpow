"""
PowPowPow — Forecast Snapshots & Counterfactual Decisions

Record predictions before outcomes exist (hash/timestamp them).
Record counterfactual decisions every day:
  For each hardware archetype, the ranked opportunity set.

Years later answer: what would an agent have done?
"""

import hashlib
import json
import os
from datetime import datetime, date
from typing import Optional, Dict, List, Any

FORECAST_DIR = '/home/box/powpowpow/warehouse/knowledge/forecasts'
DECISIONS_DIR = '/home/box/powpowpow/warehouse/knowledge/counterfactuals'


def _ensure_dir():
    os.makedirs(FORECAST_DIR, exist_ok=True)
    os.makedirs(DECISIONS_DIR, exist_ok=True)


def record_forecast(
    forecast_id: str,
    predictions: Dict[str, Any],
    model_version: str,
    confidence: float,
    created_at: Optional[str] = None,
) -> Dict:
    """
    Record a forecast before outcomes exist. Hash it for tamper-evidence.
    """
    _ensure_dir()

    if created_at is None:
        created_at = datetime.now().isoformat()

    record = {
        'forecast_id': forecast_id,
        'created_at': created_at,
        'model_version': model_version,
        'confidence': confidence,
        'predictions': predictions,
    }

    # Hash for tamper-evidence
    record_bytes = json.dumps(predictions, sort_keys=True, default=str).encode()
    record['content_hash'] = hashlib.sha256(record_bytes).hexdigest()

    today = date.today().isoformat()
    filepath = os.path.join(FORECAST_DIR, f"{today}_{forecast_id}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return record


def record_counterfactual(
    hardware_archetype: str,
    opportunity_set: List[Dict],
    best_action: str,
    best_expected_usd_hour: float,
    created_at: Optional[str] = None,
) -> Dict:
    """
    Record what a rational machine could have done at this moment.

    Args:
        hardware_archetype: e.g., 'GPU_DATACENTER_HOPPER', 'CPU_HIGH_END_DESKTOP'
        opportunity_set: Ranked list of {network, activity_type, net_usd_hour, ...}
        best_action: The best option
        best_expected_usd_hour: Expected revenue
    """
    _ensure_dir()

    if created_at is None:
        created_at = datetime.now().isoformat()

    record = {
        'hardware_archetype': hardware_archetype,
        'created_at': created_at,
        'best_action': best_action,
        'best_expected_usd_hour': best_expected_usd_hour,
        'opportunity_set': opportunity_set,
        'n_alternatives': len(opportunity_set),
    }

    # Hash
    record_bytes = json.dumps(opportunity_set, sort_keys=True, default=str).encode()
    record['content_hash'] = hashlib.sha256(record_bytes).hexdigest()

    today = date.today().isoformat()
    hardware_dir = os.path.join(DECISIONS_DIR, hardware_archetype)
    os.makedirs(hardware_dir, exist_ok=True)

    filepath = os.path.join(hardware_dir, f"{today}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return record


def get_forecast(forecast_date: str, forecast_id: str) -> Optional[Dict]:
    """Load a forecast."""
    filepath = os.path.join(FORECAST_DIR, f"{forecast_date}_{forecast_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def get_counterfactual(hardware_archetype: str, decision_date: str) -> Optional[Dict]:
    """Load a counterfactual decision."""
    filepath = os.path.join(DECISIONS_DIR, hardware_archetype, f"{decision_date}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def list_counterfactual_dates(hardware_archetype: str) -> List[str]:
    """List all dates with counterfactual decisions for a hardware type."""
    hw_dir = os.path.join(DECISIONS_DIR, hardware_archetype)
    if not os.path.exists(hw_dir):
        return []
    return sorted(f.replace('.json', '') for f in os.listdir(hw_dir) if f.endswith('.json'))


# --- Hardware archetypes ---

HARDWARE_ARCHETYPES = [
    'GPU_DATACENTER_HOPPER',     # H100, H200
    'GPU_DATACENTER_BLACKWELL',  # B200, B300
    'GPU_CONSUMER_HIGH_2026',    # RTX 4090, 5090
    'CPU_HIGH_END_DESKTOP',      # 7950X, 9950X
    'ASIC_HEAVYHASH_GEN3',       # KAS miners
]


if __name__ == '__main__':
    # Example: record a counterfactual
    record = record_counterfactual(
        hardware_archetype='GPU_DATACENTER_HOPPER',
        opportunity_set=[
            {'network': 'PRL', 'activity_type': 'mine', 'net_usd_hour': 3.42, 'confidence': 0.8},
            {'network': 'CLORE', 'activity_type': 'rent', 'net_usd_hour': 2.80, 'confidence': 0.9},
            {'network': 'AKASH', 'activity_type': 'rent', 'net_usd_hour': 2.50, 'confidence': 0.85},
            {'network': 'GNK', 'activity_type': 'inference', 'net_usd_hour': 1.90, 'confidence': 0.6},
        ],
        best_action='PRL_mine',
        best_expected_usd_hour=3.42,
    )
    print(f"Recorded: {record['hardware_archetype']} best={record['best_action']}")
    print(f"  Hash: {record['content_hash'][:16]}...")

    # List dates
    dates = list_counterfactual_dates('GPU_DATACENTER_HOPPER')
    print(f"\nDates with decisions: {dates}")
