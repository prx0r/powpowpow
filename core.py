"""
PowPowPow Core — Bitemporal, UTC-only, Auto-archiving.

Every network call automatically archives the raw response.
Every observation has event_time + observed_at (both UTC).
"""

import fcntl
import glob
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, 'warehouse', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

# Proxy support: set POW_PROXY=socks5h://127.0.0.1:9050 for Tor
POW_PROXY = os.environ.get('POW_PROXY')
if POW_PROXY:
    try:
        import socks  # noqa: F401 — enables SOCKS support in requests
    except ImportError:
        POW_PROXY = None

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
# RECOVERABILITY — backfill.md doctrine, made machine-readable
# ============================================================

# Backfillable public endpoints: re-fetch whenever needed (backfill.md).
# Prefix match on source_id. Everything else defaults to 'ephemeral',
# because unknown sources are assumed to vanish.
RECONSTRUCTABLE_SOURCE_PREFIXES = (
    'coingecko', 'kraken-ohlc', 'coinex-klines', 'gate-candles',
    'blockchaininfo-charts', 'xmrclub-mining',
    'qubic-rpc', 'qubic-query', 'qubic-analytics', 'doge-stats',
)

# Tables that are pure functions of stored rows — recompute, never hoard.
DERIVED_TABLES = frozenset({'daily_state', 'derived_signal'})

RECOVERABILITY_VALUES = ('ephemeral', 'reconstructable', 'derived', 'unknown')


def classify_recoverability(table_name: Optional[str] = None,
                   source_id: Optional[str] = None) -> str:
    """Classify one row: ephemeral (vanishes), reconstructable (re-fetch),
    derived (recompute), or unknown."""
    if table_name in DERIVED_TABLES:
        return 'derived'
    if source_id:
        sid = str(source_id)
        for prefix in RECONSTRUCTABLE_SOURCE_PREFIXES:
            if sid.startswith(prefix):
                return 'reconstructable'
    return 'ephemeral'


def load_state_file(path, default=None):
    """Read JSON tolerating absence and truncation."""
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {} if default is None else default


def atomic_json_write(path, payload):
    """Write JSON via a per-process temp file so concurrent writers cannot
    interleave into one file."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(payload, handle, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            pass


class state_lock:
    """Exclusive, blocking lock around a short read-modify-write."""

    def __init__(self, path):
        self.path = path + ".lock"

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._handle = open(self.path, "a")
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
        return False


def dict_delta(before, after):
    """Nested diff of the keys that actually changed.

    Callers load the whole file, poll the network for seconds, then write.
    Writing the whole snapshot would revert keys another process changed in
    between; this returns only what this pass touched.
    """
    delta = {}
    for key, new in after.items():
        old = before.get(key)
        if isinstance(new, dict) and isinstance(old, dict):
            changed = {k: v for k, v in new.items() if old.get(k, object()) != v}
            if changed:
                delta[key] = changed
        elif old != new:
            delta[key] = new
    return delta


def save_state_delta(path, delta):
    """Merge only the changed keys into the on-disk JSON, atomically."""
    if not delta:
        return 0
    with state_lock(path):
        current = load_state_file(path)
        for key, value in delta.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key] = {**current[key], **value}
            else:
                current[key] = value
        atomic_json_write(path, current)
    return len(delta)


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
    transport: str = 'rest',
    source_role: str = 'raw',
    event_type: Optional[str] = None,
    return_result: bool = False,
    user_agent: Optional[str] = None,
) -> Optional[Any]:
    """
    Fetch JSON with automatic raw archival.

    Every response (success, HTTP error, exception) is archived BEFORE
    parsing when archive=True. Returns the parsed payload by default;
    with return_result=True returns a FetchResult dict carrying the
    observation lineage (observation_id, timestamps, hash) so callers
    can thread raw_event_id into normalized rows.
    """
    observed_at = utcnow()
    request_started = datetime.now(timezone.utc)

    def _result(parsed, obs):
        if return_result:
            return {'parsed': parsed, 'observation_id': obs['observation_id'],
                    'observed_at': obs['observed_at'],
                    'received_at': obs['response_received'],
                    'payload_hash': obs['payload_hash'],
                    'source_id': source_id, 'transport': transport,
                    'http_status': obs['http_status']}
        return parsed

    try:
        proxies = {'http': POW_PROXY, 'https': POW_PROXY} if POW_PROXY else None
        resp = requests.get(
            url,
            params=params,
            headers={
                'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/json',
            },
            timeout=timeout,
            proxies=proxies,
        )

        response_received = utcnow()

        if resp.status_code == 200:
            try:
                parsed = resp.json()
            except:
                parsed = resp.text

            # Auto-archive raw response
            obs = None
            if archive:
                obs = _archive_raw(
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
                    transport=transport,
                    source_role=source_role,
                    event_type=event_type,
                )

            return _result(parsed, obs)

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
                transport=transport,
                source_role=source_role,
                event_type=event_type,
            )

        return _result(None, {'observation_id': None, 'observed_at': observed_at,
                              'response_received': response_received,
                              'payload_hash': None, 'http_status': resp.status_code}) \
            if return_result else None

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
                transport=transport,
                source_role=source_role,
                event_type=event_type,
            )
        return _result(None, {'observation_id': None, 'observed_at': observed_at,
                              'response_received': utcnow(),
                              'payload_hash': None, 'http_status': 0}) \
            if return_result else None

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
    transport: str = 'rest',
    source_role: str = 'raw',
    event_type: Optional[str] = None,
    recoverability: Optional[str] = None,
):
    """Archive raw response to append-only storage.

    Lossless: exact response bytes are always preserved. Bodies over
    256KB are zlib-compressed (raw_encoding='zlib-base64'); the
    payload_hash is ALWAYS over the exact original bytes, so the stored
    artifact reproduces and validates the hashed object. Writes are
    atomic (tmp + rename).
    """
    import zlib
    import base64
    payload_hash = canonical_hash(raw_body)
    event_id = raw_event_id(source_id, endpoint, observed_at, payload_hash)

    raw_bytes = raw_body.encode('utf-8') if isinstance(raw_body, str) else bytes(raw_body)
    if len(raw_bytes) > 262144:
        stored_payload = base64.b64encode(zlib.compress(raw_bytes, 6)).decode('ascii')
        raw_encoding = 'zlib-base64'
    else:
        stored_payload = raw_body
        raw_encoding = 'utf-8'

    observation = {
        'observation_id': event_id,
        'network_id': chain_id,
        'source_id': source_id,
        'transport': transport,
        'source_type': transport,  # legacy alias, same value
        'source_role': source_role,
        'event_type': event_type,
        'endpoint': endpoint,
        'request_params': request_params or {},
        'event_time': event_time,
        'observed_at': observed_at,
        'response_received': response_received,
        'http_status': http_status,
        'raw_content_type': 'application/json',
        'raw_payload': stored_payload,
        'raw_encoding': raw_encoding,
        'raw_bytes': len(raw_bytes),
        'parsed_payload': parsed_payload,
        'payload_hash': payload_hash,
        'source_version': None,
        'collector_version': '1.0.0',
        'schema_version': '1.0',
        'recoverability': recoverability or classify_recoverability(
            source_id=source_id),
        'quality_flags': quality_flags or [],
    }
    
    # Append to chain directory (atomic: tmp + rename, so ENOSPC or
    # kill can never leave a half-written observation behind).
    chain_dir = os.path.join(RAW_DIR, chain_id)
    os.makedirs(chain_dir, exist_ok=True)

    filename = f"{event_id}.json"
    filepath = os.path.join(chain_dir, filename)
    tmp_path = filepath + '.tmp'

    with open(tmp_path, 'w') as f:
        json.dump(observation, f, indent=2, default=str)
    os.replace(tmp_path, filepath)

    return {'filepath': filepath, **observation}

# ============================================================
# STORE NORMALIZED WITH LINEAGE
# ============================================================

def store_normalized(
    table_name: str,
    chain_id: str,
    data: Dict,
    raw_event_id: Optional[str] = None,
    event_time: Optional[str] = None,
    recoverability: Optional[str] = None,
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
    record['recoverability'] = recoverability or classify_recoverability(
        table_name, data.get('source_id'))
    
    normalized_dir = os.path.join(BASE_DIR, 'warehouse', 'normalized', table_name)
    os.makedirs(normalized_dir, exist_ok=True)
    
    chain_dir = os.path.join(normalized_dir, f"chain={chain_id}")
    date_dir = os.path.join(chain_dir, f"date={datetime.now(timezone.utc):%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)
    
    hour_file = os.path.join(date_dir, f"hour={datetime.now(timezone.utc):%H}.jsonl")
    
    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')
    
    return hour_file


def purge_normalized(table_name: str, field: str, value: Any) -> int:
    """Remove normalized rows whose ``field`` equals ``value``.

    Idempotent rollups (daily STATE, signals) call this before writing so a
    rerun replaces its own prior output instead of duplicating it.
    Returns the number of rows removed.
    """
    removed = 0
    root = os.path.join(BASE_DIR, 'warehouse', 'normalized', table_name)
    if not os.path.isdir(root):
        return 0
    for path in glob.glob(os.path.join(root, 'chain=*', 'date=*', 'hour=*.jsonl')):
        with open(path) as fh:
            lines = fh.readlines()
        kept = []
        changed = False
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                kept.append(line)
                continue
            if row.get(field) == value:
                removed += 1
                changed = True
            else:
                kept.append(line)
        if not changed:
            continue
        tmp = path + '.purge.tmp'
        with open(tmp, 'w') as fh:
            fh.writelines(kept)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    return removed

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
