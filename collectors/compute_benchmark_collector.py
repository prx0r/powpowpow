"""
Compute Benchmark Collector
Akash + Clore + Nosana GPU rental prices.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event

DATA_DIR = '/home/box/powpowpow/chains/benchmarks'
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_json(url, params=None, timeout=10):
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def collect_akash():
    """Collect Akash GPU capacity."""
    print("  [AKASH] Fetching provider GPU capacity...")
    
    data = fetch_json('https://api.akashnet.io/v1beta1/providers')
    providers = data.get('providers', []) if data else []
    
    # Count GPUs by model
    gpu_counts = {}
    for p in providers:
        # Parse provider attributes for GPU info
        attrs = p.get('attributes', {})
        gpu_model = attrs.get('gpu', 'unknown')
        if gpu_model not in gpu_counts:
            gpu_counts[gpu_model] = {'total': 0, 'active': 0}
        gpu_counts[gpu_model]['total'] += 1
    
    print(f"    Providers: {len(providers)}")
    print(f"    GPU models: {list(gpu_counts.keys())[:5]}")
    
    return {
        'providers': len(providers),
        'gpu_counts': gpu_counts,
    }

def collect_clore():
    """Collect Clore GPU marketplace."""
    print("  [CLORE] Fetching GPU marketplace...")
    
    data = fetch_json('https://clore.ai/api/v1/marketplace')
    servers = data if isinstance(data, list) else (data.get('servers', []) if data else [])
    
    # Analyze GPU models
    gpu_models = {}
    for s in servers:
        gpu = s.get('gpu', 'unknown')
        if gpu not in gpu_models:
            gpu_models[gpu] = {'count': 0, 'prices': []}
        gpu_models[gpu]['count'] += 1
        price = s.get('price_per_hour')
        if price:
            gpu_models[gpu]['prices'].append(float(price))
    
    print(f"    Servers: {len(servers)}")
    print(f"    GPU models: {list(gpu_models.keys())[:5]}")
    
    return {
        'servers': len(servers),
        'gpu_models': gpu_models,
    }

def collect_nosana():
    """Collect Nosana GPU markets."""
    print("  [NOSANA] Fetching GPU markets...")
    
    data = fetch_json('https://api.nosana.io/markets')
    markets = data if isinstance(data, list) else []
    
    print(f"    Markets: {len(markets)}")
    
    return {
        'markets': len(markets),
        'data': markets[:10] if markets else [],
    }

def collect_all():
    print(f"\n{'='*60}")
    print(f"Compute Benchmark Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'akash': collect_akash(),
        'clore': collect_clore(),
        'nosana': collect_nosana(),
    }
    
    filepath = f'{DATA_DIR}/compute_benchmarks.json'
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[SAVED] {filepath}")
    return results

if __name__ == '__main__':
    collect_all()
