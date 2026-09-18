"""
CLORE Collector — Append-only with auto-archive.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, '/home/box/powpowpow')
from core import fetch_json, store_normalized, utcnow

DATA_DIR = '/home/box/powpowpow/chains/clore'
os.makedirs(DATA_DIR, exist_ok=True)

def collect_marketplace():
    """Collect Clore GPU marketplace — IRREVERSIBLE data."""
    print("  [MARKETPLACE] Fetching GPU marketplace (auto-archiving)...")
    
    data = fetch_json(
        url='https://clore.ai/api/v1/marketplace',
        source_id='clore-marketplace-api',
        chain_id='clore',
    )
    
    if data:
        servers = data if isinstance(data, list) else (data.get('servers', []) if data else [])
        print(f"    Servers: {len(servers)}")
        return servers
    return []

def collect_gigaspot():
    """Collect GigaSPOT bid/ask data — IRREVERSIBLE."""
    print("  [GIGASPOT] Fetching bid/ask data (auto-archiving)...")
    
    data = fetch_json(
        url='https://gigaspot-api.clore.ai/v1/servers',
        source_id='clore-gigaspot-api',
        chain_id='clore',
    )
    
    if data:
        machines = data if isinstance(data, list) else []
        print(f"    Machines: {len(machines)}")
        return machines
    return []

def collect_price():
    """Collect CLORE price."""
    print("  [PRICE] Fetching CLORE price...")
    
    data = fetch_json(
        url='https://api.coingecko.com/api/v3/simple/price',
        params={'ids': 'clore-ai', 'vs_currencies': 'usd', 'include_market_cap': 'true'},
        source_id='coingecko',
        chain_id='clore',
    )
    
    if data and 'clore-ai' in data:
        clore = data['clore-ai']
        print(f"    CLORE: ${clore.get('usd', 'N/A')}")
        return clore
    return None

def collect_all():
    print(f"\n{'='*60}")
    print(f"CLORE Collection — {utcnow()}")
    print(f"{'='*60}")
    
    results = {
        'observed_at': utcnow(),
        'chain': 'clore',
        'marketplace': collect_marketplace(),
        'gigaspot': collect_gigaspot(),
        'price': collect_price(),
    }
    
    # Save as latest (not historical)
    filepath = os.path.join(DATA_DIR, 'latest.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
