"""
PowPowPow — Metric Versioning

Never have resource_premium without metric_version.
RP_v1 and RP_v2 coexist. Inputs must be versioned too.

Prevents silent breakage when derived equations change.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

METRICS_DIR = '/home/box/powpowpow/warehouse/knowledge/metrics'


def _ensure_dir():
    os.makedirs(METRICS_DIR, exist_ok=True)


def register_metric(
    metric_id: str,
    version: str,
    formula: str,
    inputs: Dict[str, str],
    description: str = '',
    created_at: Optional[str] = None,
) -> Dict:
    """
    Register a metric version.

    Args:
        metric_id: e.g., 'resource_premium', 'absorption_ratio'
        version: e.g., '1.0', '1.1', '2.0'
        formula: Human-readable formula description
        inputs: Dict of input_name -> metric_version or source
        description: What this metric measures

    Returns:
        Metric record
    """
    _ensure_dir()

    metric_dir = os.path.join(METRICS_DIR, metric_id)
    os.makedirs(metric_dir, exist_ok=True)

    record = {
        'metric_id': metric_id,
        'version': version,
        'formula': formula,
        'inputs': inputs,
        'description': description,
        'created_at': created_at or datetime.now().isoformat(),
    }

    filepath = os.path.join(metric_dir, f"v{version}.json")
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    # Update latest pointer
    latest_path = os.path.join(metric_dir, 'latest.json')
    with open(latest_path, 'w') as f:
        json.dump(record, f, indent=2, default=str)

    return record


def get_metric(metric_id: str, version: str = None) -> Optional[Dict]:
    """Get a metric version. If version is None, get latest."""
    metric_dir = os.path.join(METRICS_DIR, metric_id)
    if not os.path.exists(metric_dir):
        return None

    if version:
        filepath = os.path.join(metric_dir, f"v{version}.json")
    else:
        filepath = os.path.join(metric_dir, 'latest.json')

    if not os.path.exists(filepath):
        return None

    with open(filepath) as f:
        return json.load(f)


def list_metric_versions(metric_id: str) -> List[Dict]:
    """List all versions of a metric."""
    metric_dir = os.path.join(METRICS_DIR, metric_id)
    if not os.path.exists(metric_dir):
        return []

    results = []
    for fname in sorted(os.listdir(metric_dir)):
        if fname.startswith('v') and fname.endswith('.json'):
            with open(os.path.join(metric_dir, fname)) as f:
                results.append(json.load(f))
    return results


def list_all_metrics() -> List[str]:
    """List all metric IDs."""
    _ensure_dir()
    return [d for d in os.listdir(METRICS_DIR)
            if os.path.isdir(os.path.join(METRICS_DIR, d))]


if __name__ == '__main__':
    # Register some canonical metrics
    register_metric(
        metric_id='resource_premium',
        version='1.0',
        formula='ProtocolRevenuePerResourceHour - ExternalRevenuePerResourceHour',
        inputs={'price': 'ohlcv', 'emission': 'chain', 'hardware_benchmark': 'benchmark_v1'},
        description='Wedge between protocol mining return and external opportunity cost',
    )

    register_metric(
        metric_id='absorption_ratio',
        version='1.0',
        formula='(AggressiveBuy + BidAdds - BidCancels) / (AggressiveSell + MinerFlow)',
        inputs={'l2_depth': 'safetrade_ws', 'miner_flow': 'chain'},
        description='Market absorption of sell pressure',
    )

    register_metric(
        metric_id='creation_pressure',
        version='1.0',
        formula='(NewTokens * Price) / BidDepth_5pct',
        inputs={'emission': 'chain', 'price': 'ohlcv', 'depth': 'safetrade_l2'},
        description='Token creation pressure relative to bid depth',
    )

    print("Registered metrics:")
    for mid in list_all_metrics():
        versions = list_metric_versions(mid)
        print(f"  {mid}: {len(versions)} version(s)")
        for v in versions:
            print(f"    v{v['version']}: {v['formula'][:60]}")
