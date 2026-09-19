"""
PowPowPow — Source Quality Tracking

Don't merely log failures internally.
Store longitudinal source quality as part of the dataset.

Four years later you can say:
  "SafeTrade PRL L2: 99.82% coverage, 37 min total missing, longest gap 94 sec"
"""

import json
import os
from datetime import datetime, date
from typing import Optional, Dict, List

QUALITY_DIR = '/home/box/powpowpow/warehouse/knowledge/source_quality'


def _ensure_dir():
    os.makedirs(QUALITY_DIR, exist_ok=True)


def record_source_quality(
    source_id: str,
    observation_date: str = None,
    expected_observations: int = 0,
    received_observations: int = 0,
    coverage_pct: Optional[float] = None,
    largest_gap_seconds: Optional[float] = None,
    median_latency_ms: Optional[float] = None,
    p95_latency_ms: Optional[float] = None,
    schema_errors: int = 0,
    sequence_gaps: int = 0,
    reconnects: int = 0,
    confidence_grade: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> str:
    """
    Record daily source quality metrics.

    Args:
        source_id: Permanent source entity ID
        observation_date: Date string (YYYY-MM-DD)
        expected_observations: How many we expected
        received_observations: How many we got
        coverage_pct: received/expected * 100
        largest_gap_seconds: Longest gap in observations
        median_latency_ms: Median response latency
        p95_latency_ms: 95th percentile latency
        schema_errors: Number of schema validation failures
        sequence_gaps: Number of sequence number gaps
        reconnects: Number of reconnections
        confidence_grade: A/B/C/D/F
        metadata: Additional quality info

    Returns:
        Path to stored file
    """
    _ensure_dir()
    if observation_date is None:
        observation_date = date.today().isoformat()

    if coverage_pct is None and expected_observations > 0:
        coverage_pct = round(received_observations / expected_observations * 100, 2)

    if confidence_grade is None:
        if coverage_pct is not None:
            if coverage_pct >= 99.5:
                confidence_grade = 'A'
            elif coverage_pct >= 98:
                confidence_grade = 'B'
            elif coverage_pct >= 95:
                confidence_grade = 'C'
            elif coverage_pct >= 90:
                confidence_grade = 'D'
            else:
                confidence_grade = 'F'
        else:
            confidence_grade = 'unknown'

    record = {
        'source_id': source_id,
        'observation_date': observation_date,
        'recorded_at': datetime.now().isoformat(),
        'expected_observations': expected_observations,
        'received_observations': received_observations,
        'coverage_pct': coverage_pct,
        'largest_gap_seconds': largest_gap_seconds,
        'median_latency_ms': median_latency_ms,
        'p95_latency_ms': p95_latency_ms,
        'schema_errors': schema_errors,
        'sequence_gaps': sequence_gaps,
        'reconnects': reconnects,
        'confidence_grade': confidence_grade,
        'metadata': metadata or {},
    }

    source_dir = os.path.join(QUALITY_DIR, source_id)
    os.makedirs(source_dir, exist_ok=True)

    filepath = os.path.join(source_dir, f"{observation_date}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return filepath


def get_source_quality(source_id: str, observation_date: str) -> Optional[Dict]:
    """Get quality record for a source on a date."""
    filepath = os.path.join(QUALITY_DIR, source_id, f"{observation_date}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def get_source_quality_history(source_id: str) -> List[Dict]:
    """Get all quality records for a source."""
    source_dir = os.path.join(QUALITY_DIR, source_id)
    if not os.path.exists(source_dir):
        return []

    results = []
    for fname in sorted(os.listdir(source_dir)):
        if fname.endswith('.json'):
            with open(os.path.join(source_dir, fname)) as f:
                results.append(json.load(f))
    return results


def get_source_summary(source_id: str) -> Dict:
    """Get aggregate quality summary for a source over all recorded days."""
    history = get_source_quality_history(source_id)
    if not history:
        return {'source_id': source_id, 'n_days': 0}

    coverages = [r['coverage_pct'] for r in history if r.get('coverage_pct') is not None]
    latencies = [r['median_latency_ms'] for r in history if r.get('median_latency_ms') is not None]
    errors = sum(r.get('schema_errors', 0) for r in history)
    gaps = sum(r.get('sequence_gaps', 0) for r in history)

    grades = {}
    for r in history:
        g = r.get('confidence_grade', 'unknown')
        grades[g] = grades.get(g, 0) + 1

    return {
        'source_id': source_id,
        'n_days': len(history),
        'date_range': {
            'first': history[0].get('observation_date'),
            'last': history[-1].get('observation_date'),
        },
        'coverage': {
            'mean': round(sum(coverages) / len(coverages), 2) if coverages else None,
            'min': min(coverages) if coverages else None,
            'max': max(coverages) if coverages else None,
        },
        'latency': {
            'mean_ms': round(sum(latencies) / len(latencies), 2) if latencies else None,
        },
        'total_schema_errors': errors,
        'total_sequence_gaps': gaps,
        'grade_distribution': grades,
    }


def list_sources() -> List[str]:
    """List all tracked source IDs."""
    _ensure_dir()
    return [d for d in os.listdir(QUALITY_DIR)
            if os.path.isdir(os.path.join(QUALITY_DIR, d))]


if __name__ == '__main__':
    # Example: record quality for SafeTrade PRL L2
    path = record_source_quality(
        source_id='safetrade-ws-v2',
        expected_observations=1440,
        received_observations=1437,
        largest_gap_seconds=94,
        median_latency_ms=12.3,
        p95_latency_ms=45.7,
        schema_errors=0,
        sequence_gaps=2,
        reconnects=1,
    )
    print(f"Recorded: {path}")

    summary = get_source_summary('safetrade-ws-v2')
    print(f"\nSummary for safetrade-ws-v2:")
    print(f"  Days tracked: {summary['n_days']}")
    print(f"  Coverage mean: {summary['coverage']['mean']}%")
    print(f"  Latency mean: {summary['latency']['mean_ms']}ms")
