"""
PowPowPow — Experiment & Hypothesis Registry

Every experiment is frozen with full provenance:
- hypothesis, causal_chain, expected_lags, kill_conditions
- code_commit, dataset_root_hash, feature_versions
- universe_snapshot, training_window, test_window
- cost_model, execution_model, results

Hypotheses are never rewritten. Evaluations are added.

This creates a history of what ideas worked when.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

REGISTRY_DIR = '/home/box/powpowpow/warehouse/knowledge/experiments'


def _ensure_dir():
    os.makedirs(REGISTRY_DIR, exist_ok=True)


def register_hypothesis(
    hypothesis_id: str,
    description: str,
    causal_chain: List[str],
    expected_lags: List[str],
    kill_conditions: List[str],
    created_at: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Register a hypothesis (never rewrite, only add evaluations).
    """
    _ensure_dir()
    filepath = os.path.join(REGISTRY_DIR, f"{hypothesis_id}.json")

    if os.path.exists(filepath):
        with open(filepath) as f:
            record = json.load(f)
    else:
        record = {
            'hypothesis_id': hypothesis_id,
            'description': description,
            'causal_chain': causal_chain,
            'expected_lags': expected_lags,
            'kill_conditions': kill_conditions,
            'created_at': created_at or datetime.now().isoformat(),
            'metadata': metadata or {},
            'evaluations': [],
        }
        with open(filepath, 'w') as f:
            json.dump(record, f, indent=2, default=str)

    return record


def add_evaluation(
    hypothesis_id: str,
    experiment_id: str,
    code_commit: str,
    dataset_root_hash: str,
    feature_versions: Dict[str, str],
    universe_snapshot_date: str,
    training_window: Dict[str, str],
    test_window: Dict[str, str],
    cost_model: Optional[Dict] = None,
    execution_model: Optional[Dict] = None,
    results: Optional[Dict] = None,
    created_at: Optional[str] = None,
) -> Optional[Dict]:
    """
    Add an evaluation to an existing hypothesis.
    """
    _ensure_dir()
    filepath = os.path.join(REGISTRY_DIR, f"{hypothesis_id}.json")

    if not os.path.exists(filepath):
        return None

    with open(filepath) as f:
        record = json.load(f)

    evaluation = {
        'experiment_id': experiment_id,
        'created_at': created_at or datetime.now().isoformat(),
        'code_commit': code_commit,
        'dataset_root_hash': dataset_root_hash,
        'feature_versions': feature_versions,
        'universe_snapshot_date': universe_snapshot_date,
        'training_window': training_window,
        'test_window': test_window,
        'cost_model': cost_model or {},
        'execution_model': execution_model or {},
        'results': results or {},
    }

    record['evaluations'].append(evaluation)

    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return record


def get_hypothesis(hypothesis_id: str) -> Optional[Dict]:
    """Get a hypothesis record."""
    _ensure_dir()
    filepath = os.path.join(REGISTRY_DIR, f"{hypothesis_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def list_hypotheses() -> List[Dict]:
    """List all registered hypotheses."""
    _ensure_dir()
    results = []
    for fname in sorted(os.listdir(REGISTRY_DIR)):
        if fname.endswith('.json'):
            with open(os.path.join(REGISTRY_DIR, fname)) as f:
                results.append(json.load(f))
    return results


def freeze_experiment(
    experiment_id: str,
    hypothesis_id: str,
    code_commit: str,
    dataset_root_hash: str,
    feature_versions: Dict[str, str],
    universe_snapshot_date: str,
    training_window: Dict[str, str],
    test_window: Dict[str, str],
    cost_model: Optional[Dict] = None,
    execution_model: Optional[Dict] = None,
    results: Optional[Dict] = None,
) -> str:
    """
    Freeze an experiment with full provenance.
    Returns the path to the frozen experiment record.
    """
    _ensure_dir()

    record = {
        'experiment_id': experiment_id,
        'hypothesis_id': hypothesis_id,
        'frozen_at': datetime.now().isoformat(),
        'code_commit': code_commit,
        'dataset_root_hash': dataset_root_hash,
        'feature_versions': feature_versions,
        'universe_snapshot_date': universe_snapshot_date,
        'training_window': training_window,
        'test_window': test_window,
        'cost_model': cost_model or {},
        'execution_model': execution_model or {},
        'results': results or {},
    }

    filepath = os.path.join(REGISTRY_DIR, f"frozen_{experiment_id}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return filepath


if __name__ == '__main__':
    # Example: register the Seesaw hypothesis
    h = register_hypothesis(
        hypothesis_id='seesaw-001',
        description='PRL profitability shocks cause delayed GPU entry',
        causal_chain=[
            'price', 'resource_premium', 'hashrate',
            'miner_realization', 'market_pressure'
        ],
        expected_lags=['0h', '12-48h', '3-7d', '7-30d'],
        kill_conditions=[
            'no relationship after 90 days of data',
            'sign flips across train/test consistently',
        ],
    )
    print(f"Registered hypothesis: {h['hypothesis_id']}")

    # List all
    for hyp in list_hypotheses():
        print(f"  {hyp['hypothesis_id']}: {hyp['description']}")
