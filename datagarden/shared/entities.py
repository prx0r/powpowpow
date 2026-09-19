"""
DataGarden — Permanent Entity Registry

CRSP-style stable identifiers for everything.
Never let ticker, pool name, exchange symbol, GPU SKU, or wallet label
be the primary identifier.

Every entity has:
- A permanent ID that never changes
- A history of names/symbols/labels that can change
- First-seen and last-seen timestamps
- Category and metadata

This prevents the catastrophic problem of:
- Renames breaking joins
- Forks creating ambiguous references
- Dead pools/exchanges losing their identity
- Survivorship bias from only tracking current names
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

ENTITIES_DIR = Path(__file__).parent.parent / 'canonical' / 'entities'

# Entity categories
CATEGORIES = {
    'network': 'blockchain networks',
    'asset': 'tradeable tokens',
    'pool': 'mining pools',
    'exchange': 'exchanges',
    'exchange_market': 'trading pairs on exchanges',
    'hardware': 'hardware models',
    'provider': 'compute providers',
    'miner_software': 'mining software',
    'source': 'data sources',
}


def _load_entity(entity_id: str) -> Optional[Dict]:
    """Load an entity registry entry."""
    filepath = os.path.join(ENTITIES_DIR, f"{entity_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def _save_entity(entity_id: str, entity: Dict):
    """Save an entity registry entry."""
    os.makedirs(ENTITIES_DIR, exist_ok=True)
    filepath = os.path.join(ENTITIES_DIR, f"{entity_id}.json")
    with open(filepath, 'w') as f:
        json.dump(entity, f, indent=2, default=str)


def register_entity(
    entity_id: str,
    category: str,
    name: str,
    first_seen: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Register a new entity or update an existing one's current name.

    Args:
        entity_id: Permanent stable ID (e.g., 'prl-network-mainnet', 'nvidia-h100-sxm-80gb')
        category: One of CATEGORIES keys
        name: Human-readable name (can be updated later)
        first_seen: ISO timestamp when first observed
        metadata: Optional additional data

    Returns:
        Entity dict
    """
    existing = _load_entity(entity_id)

    if existing:
        # Update current name if changed
        if existing.get('current_name') != name:
            existing['name_history'].append({
                'name': name,
                'valid_from': datetime.now().isoformat(),
            })
            existing['current_name'] = name
            existing['last_updated'] = datetime.now().isoformat()
        if metadata:
            existing['metadata'].update(metadata)
        _save_entity(entity_id, existing)
        return existing

    entity = {
        'entity_id': entity_id,
        'category': category,
        'current_name': name,
        'first_seen': first_seen or datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat(),
        'status': 'active',  # active, dead, unknown
        'name_history': [{
            'name': name,
            'valid_from': first_seen or datetime.now().isoformat(),
        }],
        'metadata': metadata or {},
    }

    _save_entity(entity_id, entity)
    return entity


def update_entity(
    entity_id: str,
    name: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict] = None,
    superseded_by: Optional[str] = None,
) -> Optional[Dict]:
    """
    Update an existing entity. Never overwrite — append to history.
    """
    entity = _load_entity(entity_id)
    if not entity:
        return None

    if name and name != entity.get('current_name'):
        entity['name_history'].append({
            'name': name,
            'valid_from': datetime.now().isoformat(),
        })
        entity['current_name'] = name

    if status:
        entity['status'] = status

    if superseded_by:
        entity['superseded_by'] = superseded_by
        entity['status'] = 'superseded'

    if metadata:
        entity['metadata'].update(metadata)

    entity['last_seen'] = datetime.now().isoformat()
    entity['last_updated'] = datetime.now().isoformat()

    _save_entity(entity_id, entity)
    return entity


def get_entity(entity_id: str) -> Optional[Dict]:
    """Get entity by permanent ID."""
    return _load_entity(entity_id)


def get_entity_by_name(name: str) -> Optional[Dict]:
    """Find entity by current name (search across all entities)."""
    if not os.path.exists(ENTITIES_DIR):
        return None
    for fname in os.listdir(ENTITIES_DIR):
        if not fname.endswith('.json'):
            continue
        entity = _load_entity(fname.replace('.json', ''))
        if entity and entity.get('current_name') == name:
            return entity
    return None


def list_entities(category: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    """List all entities with optional filters."""
    if not os.path.exists(ENTITIES_DIR):
        return []

    results = []
    for fname in os.listdir(ENTITIES_DIR):
        if not fname.endswith('.json'):
            continue
        entity = _load_entity(fname.replace('.json', ''))
        if not entity:
            continue
        if category and entity.get('category') != category:
            continue
        if status and entity.get('status') != status:
            continue
        results.append(entity)

    return sorted(results, key=lambda e: e.get('first_seen', ''))


def mark_dead(entity_id: str, last_price: Optional[float] = None,
              last_hashrate: Optional[float] = None,
              failure_reason: Optional[str] = None) -> Optional[Dict]:
    """Mark an entity as dead with final observations."""
    return update_entity(
        entity_id,
        status='dead',
        metadata={
            'last_price': last_price,
            'last_hashrate': last_hashrate,
            'failure_reason': failure_reason,
            'died_at': datetime.now().isoformat(),
        }
    )


# --- Bootstrap known entities ---

KNOWN_NETWORKS = {
    'prl-network-mainnet': ('network', 'Pearl'),
    'qubic-network-mainnet': ('network', 'Qubic'),
    'nock-network-mainnet': ('network', 'Nockchain'),
    'quan-network-mainnet': ('network', 'Quantus'),
    'tsc-network-mainnet': ('network', 'TensorCash'),
    'gnk-network-mainnet': ('network', 'Gonka'),
    'xmr-network-mainnet': ('network', 'Monero'),
    'kas-network-mainnet': ('network', 'Kaspa'),
    'xel-network-mainnet': ('network', 'XEL'),
    'xtm-network-mainnet': ('network', 'Tari'),
    'npt-network-mainnet': ('network', 'NPT'),
    'qtc-network-mainnet': ('network', 'QTC'),
    'tao-network-mainnet': ('network', 'Bittensor'),
    'akt-network-mainnet': ('network', 'Akash'),
    'clore-network-mainnet': ('network', 'Clore'),
    'nos-network-mainnet': ('network', 'Nosana'),
}

KNOWN_ASSETS = {
    'prl-asset-001': ('asset', 'PRL'),
    'qubic-asset-001': ('asset', 'QUBIC'),
    'nock-asset-001': ('asset', 'NOCK'),
    'quan-asset-001': ('asset', 'QUAN'),
    'tsc-asset-001': ('asset', 'TSC'),
    'gnk-asset-001': ('asset', 'GNK'),
    'xmr-asset-001': ('asset', 'XMR'),
    'kas-asset-001': ('asset', 'KAS'),
}

KNOWN_EXCHANGES = {
    'safetrade-exchange': ('exchange', 'SafeTrade'),
    'gate-exchange': ('exchange', 'Gate'),
    'coinex-exchange': ('exchange', 'CoinEx'),
    'mexc-exchange': ('exchange', 'MEXC'),
    'bitget-exchange': ('exchange', 'Bitget'),
}

KNOWN_HARDWARE = {
    'nvidia-h100-sxm-80gb': ('hardware', 'NVIDIA H100 SXM 80GB'),
    'nvidia-h200-sxm-141gb': ('hardware', 'NVIDIA H200 SXM 141GB'),
    'nvidia-a100-sxm-80gb': ('hardware', 'NVIDIA A100 SXM 80GB'),
    'nvidia-b200': ('hardware', 'NVIDIA B200'),
    'nvidia-b300': ('hardware', 'NVIDIA B300'),
    'nvidia-rtx4090': ('hardware', 'NVIDIA RTX 4090'),
    'nvidia-rtx5090': ('hardware', 'NVIDIA RTX 5090'),
    'amd-7950x': ('hardware', 'AMD Ryzen 9 7950X'),
    'amd-9950x': ('hardware', 'AMD Ryzen 9 9950X'),
}

KNOWN_SOURCES = {
    'safetrade-ws-v2': ('source', 'SafeTrade WebSocket v2'),
    'pearltrack-api-v1': ('source', 'PearlTrack API v1'),
    'qubic-rpc-v1': ('source', 'Qubic RPC v1'),
    'akash-provider-api': ('source', 'Akash Provider API'),
    'clore-marketplace-api': ('source', 'Clore Marketplace API'),
    'priceofcompute-api': ('source', 'Price of Compute API'),
    'electricitymaps-api': ('source', 'Electricity Maps API'),
}


def bootstrap_entities():
    """Register all known entities at startup."""
    all_known = {**KNOWN_NETWORKS, **KNOWN_ASSETS, **KNOWN_EXCHANGES, **KNOWN_HARDWARE, **KNOWN_SOURCES}

    registered = 0
    for entity_id, (category, name) in all_known.items():
        existing = _load_entity(entity_id)
        if not existing:
            register_entity(entity_id, category, name)
            registered += 1

    return registered


if __name__ == '__main__':
    print("Bootstrapping entity registry...")
    n = bootstrap_entities()
    print(f"  Registered {n} new entities")

    print("\nAll networks:")
    for e in list_entities(category='network'):
        print(f"  {e['entity_id']:30} {e['current_name']:20} [{e['status']}]")

    print("\nAll hardware:")
    for e in list_entities(category='hardware'):
        print(f"  {e['entity_id']:30} {e['current_name']:20}")

    print("\nAll sources:")
    for e in list_entities(category='source'):
        print(f"  {e['entity_id']:30} {e['current_name']:20}")
