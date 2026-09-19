"""
PowPowPow Core — Bitemporal, UTC-only, Auto-archiving.

Every network call automatically archives the raw response.
Every observation has event_time + observed_at (both UTC).
"""

import json
import os
import hashlib
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, 'warehouse', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

# ============================================================
# UTC-ONLY TIMESTAMP HELPER
# ============================================================

def utcnow() -> str:
    """Return UTC ISO timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def row_date(r: Dict) -> str:
    """Point-in-time date for a normalized row: exchange/event time wins
    over our receive time (seeds carry old exchange times in new files)."""
    for k in ('exchange_time', 'event_time', 'date', 'receive_time',
              'observed_at', 'timestamp'):
        v = r.get(k)
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(
                    v / 1e6 if v > 1e12 else (v / 1e3 if v > 1e10 else v),
                    tz=timezone.utc).strftime('%Y-%m-%d')
            except (ValueError, OSError, OverflowError):
                continue
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return ''


def parse_event_time(ts) -> Optional[str]:
    """Parse an event timestamp from source, return UTC ISO or None."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except:
            return None
    return None

# ============================================================
# CANONICAL PAYLOAD HASHING
# ============================================================

def canonical_hash(payload: Any) -> str:
    """Deterministic SHA256 hash of payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def raw_event_id(source_id: str, endpoint: str, observed_at: str, payload_hash: str) -> str:
    """Content-addressed event ID."""
    key = f"{source_id}:{endpoint}:{observed_at}:{payload_hash}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]

# ============================================================
# AUTO-ARCHIVING FETCH
# ============================================================

def fetch_json(
    url: str,
    params: Optional[Dict] = None,
    timeout: int = 10,
    source_id: str = 'unknown',
    chain_id: str = 'unknown',
    archive: bool = True,
) -> Optional[Any]:
    """
    Fetch JSON with automatic raw archival.
    
    Every successful response is stored before parsing.
    """
    observed_at = utcnow()
    request_started = datetime.now(timezone.utc)
    
    try:
        resp = requests.get(
            url,
            params=params,
            headers={
                'User-Agent': 'PowPowPow/1.0',
                'Accept': 'application/json'
            },
            timeout=timeout
        )
        
        response_received = utcnow()
        
        if resp.status_code == 200:
            try:
                parsed = resp.json()
            except:
                parsed = resp.text
            
            # Auto-archive raw response
            if archive:
                _archive_raw(
                    chain_id=chain_id,
                    source_id=source_id,
                    endpoint=url,
                    event_time=None,  # Source doesn't provide event time
                    observed_at=observed_at,
                    response_received=response_received,
                    http_status=resp.status_code,
                    raw_body=resp.text,
                    parsed_payload=parsed,
                    request_params=params,
                )
            
            return parsed
        
        # Archive failures too
        if archive:
            _archive_raw(
                chain_id=chain_id,
                source_id=source_id,
                endpoint=url,
                event_time=None,
                observed_at=observed_at,
                response_received=response_received,
                http_status=resp.status_code,
                raw_body=resp.text,
                parsed_payload=None,
                request_params=params,
                quality_flags=['http_error'],
            )
        
        return None
    
    except Exception as e:
        # Archive errors
        if archive:
            _archive_raw(
                chain_id=chain_id,
                source_id=source_id,
                endpoint=url,
                event_time=None,
                observed_at=observed_at,
                response_received=utcnow(),
                http_status=0,
                raw_body=str(e),
                parsed_payload=None,
                request_params=params,
                quality_flags=['exception', str(type(e).__name__)],
            )
        return None

def _archive_raw(
    chain_id: str,
    source_id: str,
    endpoint: str,
    event_time: Optional[str],
    observed_at: str,
    response_received: str,
    http_status: int,
    raw_body: str,
    parsed_payload: Any,
    request_params: Optional[Dict] = None,
    quality_flags: Optional[list] = None,
):
    """Archive raw response to append-only storage."""
    payload_hash = canonical_hash(raw_body)
    event_id = raw_event_id(source_id, endpoint, observed_at, payload_hash)
    
    observation = {
        'observation_id': event_id,
        'network_id': chain_id,
        'source_id': source_id,
        'source_type': 'rest',
        'source_role': 'raw',
        'endpoint': endpoint,
        'request_params': request_params or {},
        'event_time': event_time,
        'observed_at': observed_at,
        'response_received': response_received,
        'http_status': http_status,
        'raw_content_type': 'application/json',
        'raw_payload': raw_body[:10000],  # Truncate very large
        'parsed_payload': parsed_payload,
        'payload_hash': payload_hash,
        'source_version': None,
        'collector_version': '1.0.0',
        'schema_version': '1.0',
        'quality_flags': quality_flags or [],
    }
    
    # Append to chain directory
    chain_dir = os.path.join(RAW_DIR, chain_id)
    os.makedirs(chain_dir, exist_ok=True)
    
    filename = f"{event_id}.json"
    filepath = os.path.join(chain_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(observation, f, indent=2, default=str)
    
    return filepath

# ============================================================
# STORE NORMALIZED WITH LINEAGE
# ============================================================

def store_normalized(
    table_name: str,
    chain_id: str,
    data: Dict,
    raw_event_id: Optional[str] = None,
    event_time: Optional[str] = None,
):
    """Store normalized data with lineage back to raw."""
    observed_at = utcnow()
    normalized_at = utcnow()
    
    record = {
        'record_id': f"{chain_id}_{table_name}_{observed_at}",
        'raw_event_id': raw_event_id,
        'network_id': chain_id,
        'event_time': event_time,
        'observed_at': observed_at,
        'normalized_at': normalized_at,
        'schema_name': table_name,
        'schema_version': '1.0',
        'normalizer_version': '1.0.0',
        **data,
    }
    
    normalized_dir = os.path.join(BASE_DIR, 'warehouse', 'normalized', table_name)
    os.makedirs(normalized_dir, exist_ok=True)
    
    chain_dir = os.path.join(normalized_dir, f"chain={chain_id}")
    date_dir = os.path.join(chain_dir, f"date={datetime.now(timezone.utc):%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)
    
    hour_file = os.path.join(date_dir, f"hour={datetime.now(timezone.utc):%H}.jsonl")
    
    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')
    
    return hour_file

# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def store_raw_event(chain_id, event_type, payload, source_info=None):
    """Legacy wrapper — calls fetch_json archiver."""
    return _archive_raw(
        chain_id=chain_id,
        source_id=source_info.get('source_id', 'unknown') if source_info else 'unknown',
        endpoint=source_info.get('endpoint', '') if source_info else '',
        event_time=None,
        observed_at=utcnow(),
        response_received=utcnow(),
        http_status=200,
        raw_body=json.dumps(payload, default=str),
        parsed_payload=payload,
        request_params=source_info.get('params', {}) if source_info else {},
    )
