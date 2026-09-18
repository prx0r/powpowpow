"""
Data Quality Telemetry
Tracks collector health and coverage.
"""

import json
import os
from datetime import datetime, timezone
import sys

sys.path.insert(0, '/home/box/powpowpow')
from core import utcnow

DATA_DIR = '/home/box/powpowpow/warehouse/quality'
os.makedirs(DATA_DIR, exist_ok=True)

def record_collector_run(
    collector_id: str,
    started_at: str,
    finished_at: str,
    success: bool,
    observations_received: int = 0,
    observations_written: int = 0,
    source_latency_ms: int = 0,
    http_status: int = 0,
    parse_errors: int = 0,
    last_event_time: str = None,
    gap_detected: bool = False,
    schema_version: str = '1.0',
    collector_version: str = '1.0.0',
    error_message: str = None,
):
    """Record a collector run for quality telemetry."""
    record = {
        'record_id': f"{collector_id}_{utcnow()}",
        'collector_id': collector_id,
        'started_at': started_at,
        'finished_at': finished_at,
        'duration_seconds': (datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds(),
        'success': success,
        'observations_received': observations_received,
        'observations_written': observations_written,
        'source_latency_ms': source_latency_ms,
        'http_status': http_status,
        'parse_errors': parse_errors,
        'last_event_time': last_event_time,
        'lag_seconds': None,
        'gap_detected': gap_detected,
        'schema_version': schema_version,
        'collector_version': collector_version,
        'error_message': error_message,
    }
    
    # Calculate lag
    if last_event_time:
        try:
            event_dt = datetime.fromisoformat(last_event_time)
            record_dt = datetime.fromisoformat(finished_at)
            record['lag_seconds'] = (record_dt - event_dt).total_seconds()
        except:
            pass
    
    # Append to daily log
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_file = os.path.join(DATA_DIR, f'{date_str}.jsonl')
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')
    
    return record

def get_coverage_stats(collector_id: str, date: str = None):
    """Calculate coverage stats for a collector."""
    if date is None:
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    log_file = os.path.join(DATA_DIR, f'{date}.jsonl')
    if not os.path.exists(log_file):
        return {'collector_id': collector_id, 'coverage_pct': 0, 'runs': 0}
    
    runs = []
    with open(log_file) as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                if record.get('collector_id') == collector_id:
                    runs.append(record)
    
    if not runs:
        return {'collector_id': collector_id, 'coverage_pct': 0, 'runs': 0}
    
    successful = sum(1 for r in runs if r.get('success'))
    
    return {
        'collector_id': collector_id,
        'date': date,
        'runs': len(runs),
        'successful': successful,
        'coverage_pct': successful / len(runs) * 100 if runs else 0,
        'avg_latency_ms': sum(r.get('source_latency_ms', 0) for r in runs) / len(runs) if runs else 0,
        'total_observations': sum(r.get('observations_written', 0) for r in runs),
        'gaps_detected': sum(1 for r in runs if r.get('gap_detected')),
    }
