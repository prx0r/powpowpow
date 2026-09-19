"""
DataGarden — Unified Normalization Layer

Provides a single interface for normalizing data from all four gardens
into canonical form: Breadup, UKGraph, PowPowPow, and UKAdmin.

Usage:
    from datagarden.shared.normalize import (
        normalize_from_source,
        load_canonical,
        search_canonical,
        get_stats,
    )

    # Normalize from any source
    record = normalize_from_source('breadup', 'sold_comps', raw_data)

    # Load all canonical data
    records = load_canonical('ukgraph', limit=100)

    # Search
    results = search_canonical('powpowpow', 'RTX 4090', limit=20)

    # Stats
    stats = get_stats('breadup')
"""

import json
import os
import re
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------

DATAGARDEN_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_ROOT = DATAGARDEN_ROOT / 'canonical'

GARDENS = {
    'breadup': CANONICAL_ROOT / 'breadup',
    'ukgraph': CANONICAL_ROOT / 'ukgraph',
    'powpowpow': CANONICAL_ROOT / 'powpowpow',
    'ukadmin': CANONICAL_ROOT / 'ukadmin',
}

# ---------------------------------------------------------------------------
# Thread-safe JSONL writer
# ---------------------------------------------------------------------------

_locks: Dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_lock(filepath: str) -> threading.Lock:
    """Get or create a lock for a specific file path."""
    with _locks_lock:
        if filepath not in _locks:
            _locks[filepath] = threading.Lock()
        return _locks[filepath]


def _append_jsonl(filepath: Path, records: List[dict]) -> int:
    """Thread-safe append to JSONL file. Returns count written."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    lock = _get_lock(str(filepath))
    with lock:
        with open(filepath, 'a') as f:
            count = 0
            for rec in records:
                f.write(json.dumps(rec, default=str) + '\n')
                count += 1
        return count


def _read_jsonl(filepath: Path, limit: int = 0) -> List[dict]:
    """Read records from a JSONL file with optional limit."""
    records = []
    if not filepath.exists():
        return records
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
    return records


def _read_all_jsonl(directory: Path, limit: int = 0) -> List[dict]:
    """Read all JSONL files in a directory tree."""
    records = []
    if not directory.exists():
        return records
    for root, dirs, files in os.walk(directory):
        for fname in sorted(files):
            if fname.endswith('.jsonl'):
                filepath = Path(root) / fname
                remaining = limit - len(records) if limit else 0
                records.extend(_read_jsonl(filepath, remaining))
                if limit and len(records) >= limit:
                    return records[:limit]
    return records


# ---------------------------------------------------------------------------
# Canonical Schemas
# ---------------------------------------------------------------------------

@dataclass
class BreadupCanonical:
    """Breadup garden canonical record — physical goods & flips."""
    object_id: str          # permanent ID
    canonical_name: str     # normalized name
    category: str           # top-level category
    subcategory: str        # specific type
    brand: str              # manufacturer
    model: str              # specific model
    condition: str          # new/used_like_new/used_good/used_fair/parts
    sold_price_gbp: float   # actual sold price
    original_price_gbp: float  # original/listed price (if known)
    platform: str           # ebay_uk/vinted/facebook/gumtree
    sold_date: str          # YYYY-MM-DD
    source: str             # collector source
    observed_at: str        # ISO timestamp
    # Optional fields
    shipping_gbp: float = 0.0
    seller_rating: float = 0.0
    listing_age_days: int = 0
    category_slug: str = ''  # normalized slug for search


@dataclass
class UKGraphCanonical:
    """UKGraph garden canonical record — UK economic data."""
    series_id: str          # permanent ID
    metric: str             # employment_rate/median_pay/business_count/etc
    dimension: str          # occupation/region/sector/time
    dimension_value: str    # SOC code, region code, SIC code
    dimension_name: str     # human-readable name
    period: str             # YYYY-Q1/YYYY/YYYY-MM
    value: float            # measured value
    unit: str               # rate/GBP/count/index
    source: str             # nomis/ashe/companies_house/land_registry
    observed_at: str        # ISO timestamp
    # Optional fields
    region_code: str = ''
    region_name: str = ''
    parent_metric: str = ''  # what this metric is part of
    confidence: float = 1.0
    sample_size: int = 0


@dataclass
class PowPowPowCanonical:
    """PowPowPow garden canonical record — mining economics."""
    symbol: str             # chain symbol
    metric: str             # price/network_stats/hardware_benchmark/profitability
    timestamp: str          # ISO timestamp
    # For price metrics
    price_usd: float = 0.0
    market_cap: float = 0.0
    volume_24h: float = 0.0
    # For network metrics
    hashrate: float = 0.0
    difficulty: float = 0.0
    block_reward: float = 0.0
    block_time: float = 0.0
    # For hardware metrics
    device: str = ''
    algorithm: str = ''
    hashrate_mhs: float = 0.0
    power_watts: float = 0.0
    # For profitability metrics
    revenue_usd_day: float = 0.0
    electricity_usd_day: float = 0.0
    net_profit_usd_day: float = 0.0
    # Common fields
    source: str = ''
    observed_at: str = ''


@dataclass
class UKAdminCanonical:
    """UKAdmin garden canonical record — UK government admin tasks."""
    task_id: str
    task_name: str
    category: str          # driving, tax, business, home, benefits, passport, vehicle
    subcategory: str
    authority: str         # DVLA, HMRC, DVSA, Home Office, etc
    jurisdiction: str      # GB, England, Scotland, Wales, NI
    url: str
    cost_gbp: float = 0.0
    takes_time: str = ''
    requires: str = ''     # JSON list stored as string
    agent_permissions: str = ''  # JSON dict stored as string
    failure_modes: str = ''      # JSON list stored as string
    official_source: str = ''
    last_verified: str = ''
    is_recurring: bool = False
    recurrence: str = ''
    related_tasks: str = ''      # JSON list stored as string
    commercial_needs: str = ''   # JSON list stored as string
    source: str = 'govuk'
    observed_at: str = ''


# ---------------------------------------------------------------------------
# Normalizers — map source-specific data to canonical form
# ---------------------------------------------------------------------------

def _normalize_breadup(source: str, raw: dict) -> BreadupCanonical:
    """Normalize Breadup raw data to canonical form."""
    now = datetime.now(timezone.utc).isoformat()

    # Try to extract fields with sensible defaults
    obj_id = raw.get('object_id') or raw.get('id') or raw.get('listing_id', '')
    name = raw.get('canonical_name') or raw.get('title') or raw.get('name', '')
    category = raw.get('category') or raw.get('primary_category', '')
    subcategory = raw.get('subcategory') or raw.get('item_type', '')
    brand = raw.get('brand') or raw.get('manufacturer', '')
    model = raw.get('model') or raw.get('product_model', '')
    condition = raw.get('condition') or _map_condition(raw.get('condition_id', ''))

    sold_price = _float(raw.get('sold_price_gbp') or raw.get('sold_price') or raw.get('price', 0))
    orig_price = _float(raw.get('original_price_gbp') or raw.get('list_price') or raw.get('original_price', 0))
    shipping = _float(raw.get('shipping_gbp') or raw.get('shipping_cost', 0))
    seller_rating = _float(raw.get('seller_rating') or raw.get('feedback_score', 0))
    listing_age = _int(raw.get('listing_age_days') or raw.get('age_days', 0))

    platform = raw.get('platform') or _detect_platform(source, raw)
    sold_date = raw.get('sold_date') or raw.get('end_date') or ''
    if sold_date and 'T' in str(sold_date):
        sold_date = str(sold_date).split('T')[0]

    category_slug = raw.get('category_slug') or _slugify(category)

    return BreadupCanonical(
        object_id=obj_id,
        canonical_name=name,
        category=category,
        subcategory=subcategory,
        brand=brand,
        model=model,
        condition=condition,
        sold_price_gbp=sold_price,
        original_price_gbp=orig_price,
        platform=platform,
        sold_date=sold_date,
        source=source,
        observed_at=raw.get('observed_at') or now,
        shipping_gbp=shipping,
        seller_rating=seller_rating,
        listing_age_days=listing_age,
        category_slug=category_slug,
    )


def _normalize_ukgraph(source: str, raw: dict) -> UKGraphCanonical:
    """Normalize UKGraph raw data to canonical form."""
    now = datetime.now(timezone.utc).isoformat()

    series_id = raw.get('series_id') or raw.get('id', '')
    metric = raw.get('metric') or raw.get('indicator', '')
    dimension = raw.get('dimension') or raw.get('dimension_type', '')
    dimension_value = raw.get('dimension_value') or raw.get('code', '')
    dimension_name = raw.get('dimension_name') or raw.get('label', '')
    period = raw.get('period') or raw.get('time') or raw.get('date', '')
    value = _float(raw.get('value') or raw.get('measure_value', 0))
    unit = raw.get('unit') or raw.get('measure_unit', '')
    source_id = raw.get('source') or source

    region_code = raw.get('region_code') or raw.get('geography_code', '')
    region_name = raw.get('region_name') or raw.get('geography_name', '')
    parent_metric = raw.get('parent_metric') or raw.get('parent_indicator', '')
    confidence = _float(raw.get('confidence', 1.0))
    sample_size = _int(raw.get('sample_size') or raw.get('n', 0))

    return UKGraphCanonical(
        series_id=series_id,
        metric=metric,
        dimension=dimension,
        dimension_value=dimension_value,
        dimension_name=dimension_name,
        period=str(period),
        value=value,
        unit=unit,
        source=source_id,
        observed_at=raw.get('observed_at') or now,
        region_code=region_code,
        region_name=region_name,
        parent_metric=parent_metric,
        confidence=confidence,
        sample_size=sample_size,
    )


def _normalize_powpowpow(source: str, raw: dict) -> PowPowPowCanonical:
    """Normalize PowPowPow raw data to canonical form."""
    now = datetime.now(timezone.utc).isoformat()

    symbol = raw.get('symbol') or raw.get('chain', '')
    metric = raw.get('metric') or raw.get('event_type') or raw.get('type', '')
    timestamp = raw.get('timestamp') or raw.get('time') or raw.get('observed_at') or now

    price_usd = _float(raw.get('price_usd') or raw.get('price', 0))
    market_cap = _float(raw.get('market_cap', 0))
    volume_24h = _float(raw.get('volume_24h') or raw.get('volume', 0))

    hashrate = _float(raw.get('hashrate') or raw.get('network_hashrate', 0))
    difficulty = _float(raw.get('difficulty') or raw.get('network_difficulty', 0))
    block_reward = _float(raw.get('block_reward') or raw.get('reward', 0))
    block_time = _float(raw.get('block_time') or raw.get('block_time_avg', 0))

    device = raw.get('device') or raw.get('gpu_model') or raw.get('hardware', '')
    algorithm = raw.get('algorithm') or raw.get('algo', '')
    hashrate_mhs = _float(raw.get('hashrate_mhs') or raw.get('hashrate_megahash', 0))
    power_watts = _float(raw.get('power_watts') or raw.get('power') or raw.get('consumption', 0))

    revenue_usd_day = _float(raw.get('revenue_usd_day') or raw.get('daily_revenue', 0))
    electricity_usd_day = _float(raw.get('electricity_usd_day') or raw.get('daily_electricity_cost', 0))
    net_profit_usd_day = _float(raw.get('net_profit_usd_day') or raw.get('daily_profit', 0))

    return PowPowPowCanonical(
        symbol=symbol,
        metric=metric,
        timestamp=str(timestamp),
        price_usd=price_usd,
        market_cap=market_cap,
        volume_24h=volume_24h,
        hashrate=hashrate,
        difficulty=difficulty,
        block_reward=block_reward,
        block_time=block_time,
        device=device,
        algorithm=algorithm,
        hashrate_mhs=hashrate_mhs,
        power_watts=power_watts,
        revenue_usd_day=revenue_usd_day,
        electricity_usd_day=electricity_usd_day,
        net_profit_usd_day=net_profit_usd_day,
        source=source,
        observed_at=raw.get('observed_at') or now,
    )


def _normalize_ukadmin(source: str, raw: dict) -> UKAdminCanonical:
    """Normalize UKAdmin raw data to canonical form."""
    now = datetime.now(timezone.utc).isoformat()

    task_id = raw.get('task_id', '')
    task_name = raw.get('task_name', '')
    category = raw.get('category', '')
    subcategory = raw.get('subcategory', '')
    authority = raw.get('authority', '')
    jurisdiction = raw.get('jurisdiction', 'GB')
    url = raw.get('url', '')
    cost_gbp = _float(raw.get('cost_gbp', 0))
    takes_time = raw.get('takes_time', '')
    official_source = raw.get('official_source', '')
    last_verified = raw.get('last_verified', '')
    is_recurring = raw.get('is_recurring', False)
    recurrence = raw.get('recurrence', '')

    # Store lists/dicts as JSON strings for JSONL compatibility
    import json as _json
    requires = _json.dumps(raw.get('requires', []))
    agent_permissions = _json.dumps(raw.get('agent_permissions', {}))
    failure_modes = _json.dumps(raw.get('failure_modes', []))
    related_tasks = _json.dumps(raw.get('related_tasks', []))
    commercial_needs = _json.dumps(raw.get('commercial_needs', []))

    return UKAdminCanonical(
        task_id=task_id,
        task_name=task_name,
        category=category,
        subcategory=subcategory,
        authority=authority,
        jurisdiction=jurisdiction,
        url=url,
        cost_gbp=cost_gbp,
        takes_time=takes_time,
        requires=requires,
        agent_permissions=agent_permissions,
        failure_modes=failure_modes,
        official_source=official_source,
        last_verified=last_verified,
        is_recurring=is_recurring,
        recurrence=recurrence,
        related_tasks=related_tasks,
        commercial_needs=commercial_needs,
        source=source,
        observed_at=raw.get('observed_at') or now,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _float(val: Any) -> float:
    """Safe float conversion."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _int(val: Any) -> int:
    """Safe int conversion."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def _map_condition(condition_id: Any) -> str:
    """Map raw condition IDs to canonical condition strings."""
    mapping = {
        '1': 'new',
        '2': 'used_like_new',
        '3': 'used_good',
        '4': 'used_fair',
        '5': 'parts',
        'new': 'new',
        'like new': 'used_like_new',
        'like_new': 'used_like_new',
        'very good': 'used_good',
        'good': 'used_good',
        'acceptable': 'used_fair',
        'fair': 'used_fair',
        'for parts': 'parts',
        'parts': 'parts',
    }
    key = str(condition_id).lower().strip()
    return mapping.get(key, 'unknown')


def _detect_platform(source: str, raw: dict) -> str:
    """Detect selling platform from source or raw data."""
    source_lower = source.lower()
    if 'ebay' in source_lower:
        return 'ebay_uk'
    if 'vinted' in source_lower:
        return 'vinted'
    if 'facebook' in source_lower or 'fb' in source_lower:
        return 'facebook'
    if 'gumtree' in source_lower:
        return 'gumtree'
    # Check raw data
    url = raw.get('url', '') or raw.get('listing_url', '')
    if 'ebay.co.uk' in url or 'ebay.com' in url:
        return 'ebay_uk'
    if 'vinted' in url:
        return 'vinted'
    if 'facebook.com/marketplace' in url:
        return 'facebook'
    if 'gumtree' in url:
        return 'gumtree'
    return raw.get('platform', 'unknown')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

NORMALIZERS = {
    'breadup': _normalize_breadup,
    'ukgraph': _normalize_ukgraph,
    'powpowpow': _normalize_powpowpow,
    'ukadmin': _normalize_ukadmin,
}

SCHEMA_CLASSES = {
    'breadup': BreadupCanonical,
    'ukgraph': UKGraphCanonical,
    'powpowpow': PowPowPowCanonical,
    'ukadmin': UKAdminCanonical,
}


def normalize_from_source(garden: str, source: str, raw_data: dict) -> dict:
    """
    Normalize raw data from any source into canonical form.

    Args:
        garden: 'breadup', 'ukgraph', 'powpowpow', or 'ukadmin'
        source: source identifier (e.g., 'sold_comps', 'nomis', 'coingecko')
        raw_data: raw record from the source

    Returns:
        Normalized canonical record as dict

    Raises:
        ValueError: if garden is unknown
    """
    garden = garden.lower().strip()
    if garden not in NORMALIZERS:
        raise ValueError(f"Unknown garden: {garden!r}. Must be one of: {list(NORMALIZERS.keys())}")

    normalizer = NORMALIZERS[garden]
    canonical_obj = normalizer(source, raw_data)
    return asdict(canonical_obj)


def store_canonical(garden: str, record: dict) -> str:
    """
    Store a canonical record to the garden's JSONL file.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        record: canonical record dict

    Returns:
        Path to the JSONL file written
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    garden_dir = GARDENS[garden]
    garden_dir.mkdir(parents=True, exist_ok=True)

    # Partition by date
    observed = record.get('observed_at', '')
    if observed and 'T' in observed:
        date_str = observed.split('T')[0]
    else:
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    filepath = garden_dir / f"{date_str}.jsonl"
    _append_jsonl(filepath, [record])
    return str(filepath)


def store_canonical_batch(garden: str, records: List[dict]) -> str:
    """
    Store a batch of canonical records.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        records: list of canonical record dicts

    Returns:
        Path to the JSONL file written
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    garden_dir = GARDENS[garden]
    garden_dir.mkdir(parents=True, exist_ok=True)

    # Partition by date — group records by observed date
    by_date: Dict[str, List[dict]] = {}
    for rec in records:
        observed = rec.get('observed_at', '')
        if observed and 'T' in observed:
            date_str = observed.split('T')[0]
        else:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        by_date.setdefault(date_str, []).append(rec)

    last_path = ''
    for date_str, batch in by_date.items():
        filepath = garden_dir / f"{date_str}.jsonl"
        _append_jsonl(filepath, batch)
        last_path = str(filepath)

    return last_path


def load_canonical(garden: str, limit: int = 1000) -> List[dict]:
    """
    Load all canonical records for a garden.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        limit: maximum number of records to return (0 for all)

    Returns:
        List of canonical record dicts
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    garden_dir = GARDENS[garden]
    return _read_all_jsonl(garden_dir, limit)


def search_canonical(garden: str, query: str, limit: int = 50) -> List[dict]:
    """
    Search canonical records by text query.

    Searches across all string fields in the canonical records.
    Case-insensitive substring matching.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        query: search query string
        limit: maximum results to return

    Returns:
        List of matching canonical record dicts
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    query_lower = query.lower()
    all_records = load_canonical(garden, limit=0)

    matches = []
    for rec in all_records:
        # Search all string values in the record
        for val in rec.values():
            if isinstance(val, str) and query_lower in val.lower():
                matches.append(rec)
                break
            elif isinstance(val, (int, float)) and query_lower in str(val):
                matches.append(rec)
                break

        if limit and len(matches) >= limit:
            break

    return matches


def get_stats(garden: str) -> dict:
    """
    Get statistics for a garden.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'

    Returns:
        Dict with keys: record_count, latest_date, earliest_date, sources, file_count
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    garden_dir = GARDENS[garden]

    stats = {
        'garden': garden,
        'record_count': 0,
        'latest_date': '',
        'earliest_date': '',
        'sources': [],
        'file_count': 0,
        'total_bytes': 0,
    }

    if not garden_dir.exists():
        return stats

    dates = []
    sources = set()
    total_records = 0

    for root, dirs, files in os.walk(garden_dir):
        for fname in files:
            if not fname.endswith('.jsonl'):
                continue

            filepath = Path(root) / fname
            stats['file_count'] += 1
            stats['total_bytes'] += filepath.stat().st_size

            # Extract date from filename
            date_str = fname.replace('.jsonl', '')
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                dates.append(date_str)

            # Read records for source counting
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    total_records += 1
                    try:
                        rec = json.loads(line)
                        src = rec.get('source', '')
                        if src:
                            sources.add(src)
                    except json.JSONDecodeError:
                        continue

    stats['record_count'] = total_records
    stats['sources'] = sorted(sources)
    if dates:
        stats['latest_date'] = max(dates)
        stats['earliest_date'] = min(dates)

    return stats


def clear_garden(garden: str) -> int:
    """
    Clear all canonical data for a garden.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'

    Returns:
        Number of files removed
    """
    garden = garden.lower().strip()
    if garden not in GARDENS:
        raise ValueError(f"Unknown garden: {garden!r}")

    garden_dir = GARDENS[garden]
    if not garden_dir.exists():
        return 0

    count = 0
    for root, dirs, files in os.walk(garden_dir, topdown=False):
        for fname in files:
            if fname.endswith('.jsonl'):
                os.remove(os.path.join(root, fname))
                count += 1
        for d in dirs:
            os.rmdir(os.path.join(root, d))

    return count


# ---------------------------------------------------------------------------
# Convenience: normalize + store in one call
# ---------------------------------------------------------------------------

def ingest(garden: str, source: str, raw_data: dict) -> dict:
    """
    Normalize raw data and store it in one step.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        source: source identifier
        raw_data: raw record from the source

    Returns:
        The normalized canonical record
    """
    record = normalize_from_source(garden, source, raw_data)
    store_canonical(garden, record)
    return record


def ingest_batch(garden: str, source: str, raw_records: List[dict]) -> List[dict]:
    """
    Normalize and store a batch of raw records.

    Args:
        garden: 'breadup', 'ukgraph', or 'powpowpow'
        source: source identifier
        raw_records: list of raw records from the source

    Returns:
        List of normalized canonical records
    """
    canonical = [normalize_from_source(garden, source, r) for r in raw_records]
    if canonical:
        store_canonical_batch(garden, canonical)
    return canonical


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python normalize.py <command> [args]")
        print("Commands:")
        print("  stats <garden>              - Show garden statistics")
        print("  search <garden> <query>     - Search canonical records")
        print("  load <garden> [limit]       - Load canonical records")
        print("  test                        - Run integration test")
        return

    cmd = sys.argv[1]

    if cmd == 'stats':
        garden = sys.argv[2] if len(sys.argv) > 2 else 'breadup'
        stats = get_stats(garden)
        print(json.dumps(stats, indent=2))

    elif cmd == 'search':
        if len(sys.argv) < 4:
            print("Usage: python normalize.py search <garden> <query>")
            return
        garden = sys.argv[2]
        query = sys.argv[3]
        results = search_canonical(garden, query)
        print(f"Found {len(results)} results:")
        for r in results[:10]:
            print(json.dumps(r, indent=2))

    elif cmd == 'load':
        garden = sys.argv[2] if len(sys.argv) > 2 else 'breadup'
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        records = load_canonical(garden, limit)
        print(f"Loaded {len(records)} records:")
        for r in records[:5]:
            print(json.dumps(r, indent=2))

    elif cmd == 'test':
        print("=== Normalization Layer Integration Test ===\n")

        # Test Breadup
        print("1. Breadup normalization...")
        raw_breadup = {
            'title': 'Sony WH-1000XM5 Headphones',
            'category': 'Electronics',
            'subcategory': 'Headphones',
            'brand': 'Sony',
            'model': 'WH-1000XM5',
            'condition': 'like new',
            'sold_price': 189.99,
            'list_price': 299.99,
            'platform': 'ebay_uk',
            'sold_date': '2026-09-15',
        }
        rec = normalize_from_source('breadup', 'ebay_sold', raw_breadup)
        store_canonical('breadup', rec)
        print(f"   Normalized: {rec['canonical_name']}")
        print(f"   Price: £{rec['sold_price_gbp']}")

        # Test UKGraph
        print("\n2. UKGraph normalization...")
        raw_ukgraph = {
            'indicator': 'Employment Rate',
            'geography_code': 'E12000001',
            'geography_name': 'North East',
            'time': '2026-Q2',
            'measure_value': 71.2,
            'measure_unit': 'rate',
        }
        rec = normalize_from_source('ukgraph', 'nomis', raw_ukgraph)
        store_canonical('ukgraph', rec)
        print(f"   Normalized: {rec['metric']}")
        print(f"   Value: {rec['value']} {rec['unit']}")

        # Test PowPowPow
        print("\n3. PowPowPow normalization...")
        raw_powpowpow = {
            'symbol': 'XMR',
            'event_type': 'price',
            'price': 165.42,
            'market_cap': 3050000000,
            'volume': 85000000,
        }
        rec = normalize_from_source('powpowpow', 'coingecko', raw_powpowpow)
        store_canonical('powpowpow', rec)
        print(f"   Normalized: {rec['symbol']}")
        print(f"   Price: ${rec['price_usd']}")

        # Test search
        print("\n4. Search test...")
        results = search_canonical('breadup', 'Sony')
        print(f"   Found {len(results)} results for 'Sony'")

        # Test stats
        print("\n5. Stats test...")
        for g in ['breadup', 'ukgraph', 'powpowpow']:
            s = get_stats(g)
            print(f"   {g}: {s['record_count']} records, sources: {s['sources']}")

        print("\n=== All tests passed ===")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == '__main__':
    main()
