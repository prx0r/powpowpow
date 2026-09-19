"""
AKT (Akash) Collector
Decentralized GPU/CPU capacity market.
"""

import json
import os
import time
from datetime import datetime, timezone
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from core import fetch_json, store_normalized, utcnow

DATA_DIR = os.path.join(BASE_DIR, 'chains', 'akt')
os.makedirs(DATA_DIR, exist_ok=True)


def collect_provider_data():
    """Collect Akash provider GPU inventory."""
    print("  [PROVIDERS] Fetching provider data...")
    
    # Akash REST API
    data = fetch_json('https://api.akashnet.io/v1beta1/providers', source_id='legacy', chain_id='venue')
    if data:
        providers = data.get('providers', [])
        print(f"    Providers: {len(providers)}")
        
        # Store raw
        store_raw_event('akt', 'providers', data, {
            'source_id': 'akash-api',
            'source_type': 'rest',
        })
        
        return providers
    
    # Try alternative
    data = fetch_json('https://api.cloudmos.io/v1/providers', source_id='legacy', chain_id='venue')
    if data:
        print(f"    Providers: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_gpu_availability():
    """Collect GPU availability data."""
    print("  [GPU] Fetching GPU availability...")
    
    data = fetch_json('https://api.cloudmos.io/v1/gpu-models', source_id='legacy', chain_id='venue')
    if data:
        print(f"    GPU models: {len(data) if isinstance(data, list) else 'N/A'}")
        return data
    
    return None

def collect_market_data():
    """Collect AKT market data."""
    print("  [MARKET] Fetching market data...")
    
    data = fetch_json('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': 'akash-network',
        'vs_currencies': 'usd',
        'include_market_cap': 'true',
        'include_24hr_vol': 'true'
    })
    if data and 'akash-network' in data:
        akt_data = data['akash-network']
        print(f"    AKT: ${akt_data.get('usd', 'N/A')}")
        return akt_data
    
    return None

def collect_leases():
    """Collect active leases (deployment data)."""
    print("  [LEASES] Fetching lease data...")
    
    data = fetch_json('https://api.akashnet.io/v1beta1/leases', source_id='legacy', chain_id='venue')
    if data:
        leases = data.get('leases', [])
        print(f"    Active leases: {len(leases)}")
        return leases
    
    return None

def collect_all():
    """Collect all AKT data."""
    print(f"\n{'='*60}")
    print(f"AKT (Akash) Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'providers': collect_provider_data(),
        'gpus': collect_gpu_availability(),
        'market': collect_market_data(),
        'leases': collect_leases(),
    }
    
    # Save
    filepath = os.path.join(DATA_DIR, 'akt_data.json')
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
