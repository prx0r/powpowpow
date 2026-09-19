"""Storage for core objects. All writes are append-only, thread-safe, and date-partitioned."""

import json
import os
import threading
from pathlib import Path
from datetime import datetime, timezone

DATA_ROOT = Path(__file__).parent.parent / "canonical"

_locks = {}

def _get_lock(filepath: Path) -> threading.Lock:
    key = str(filepath)
    if key not in _locks:
        _locks[key] = threading.Lock()
    return _locks[key]

def store_observation(obs) -> str:
    """Store an observation. Returns the observation_id."""
    garden = obs.garden if hasattr(obs, 'garden') else obs.get('garden', 'unknown')
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = DATA_ROOT / garden / f"{date}.jsonl"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    record = obs.to_dict() if hasattr(obs, 'to_dict') else obs

    lock = _get_lock(filepath)
    with lock:
        with open(filepath, 'a') as f:
            f.write(json.dumps(record, default=str) + '\n')

    return record.get('observation_id', '')

def store_observation_batch(observations: list) -> int:
    """Store multiple observations. Returns count stored."""
    count = 0
    for obs in observations:
        store_observation(obs)
        count += 1
    return count

def load_observations(garden: str, limit: int = 1000, date: str = None) -> list:
    """Load observations for a garden."""
    garden_dir = DATA_ROOT / garden
    if not garden_dir.exists():
        return []

    results = []
    files = sorted(garden_dir.glob("*.jsonl"), reverse=True)
    if date:
        files = [f for f in files if f.stem == date]

    for f in files:
        with open(f) as fh:
            for line in fh:
                try:
                    results.append(json.loads(line))
                    if len(results) >= limit:
                        return results
                except json.JSONDecodeError:
                    continue
    return results

def search_observations(garden: str, query: str, limit: int = 50) -> list:
    """Search observations by text query."""
    all_obs = load_observations(garden, limit=10000)
    results = []
    query_lower = query.lower()

    for obs in all_obs:
        text = json.dumps(obs, default=str).lower()
        if query_lower in text:
            results.append(obs)
            if len(results) >= limit:
                break

    return results
