"""
QUBIC Data Collector — Phase 1
Pulls from official Qubic RPC and static registry.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys
sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event, store_normalized

BASE_URL = 'https://rpc.qubic.org/v1'
STATIC_URL = 'https://static.qubic.org/v1'

def fetch_json(url, params=None, timeout=15):
    """Fetch JSON from endpoint."""
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None

def collect_tick_info():
    """Collect current tick information."""
    print("  [TICK] Fetching tick info...")
    
    data = fetch_json(f'{BASE_URL}/tick-info')
    if data:
        # Store raw
        store_raw_event('qubic', 'tick_info', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
            'endpoint': f'{BASE_URL}/tick-info',
        })
        
        # Normalize
        tick_data = data.get('tick', data)
        store_normalized('chain_snapshot', 'qubic', {
            'height': tick_data.get('tick', tick_data.get('tickNumber')),
            'epoch': tick_data.get('epoch'),
            'tip_hash': tick_data.get('hash'),
            'tx_count': tick_data.get('txCount'),
        })
        
        print(f"    Tick: {tick_data.get('tick', tick_data.get('tickNumber'))}")
        print(f"    Epoch: {tick_data.get('epoch')}")
        print(f"    TX count: {tick_data.get('txCount')}")
        
        return data
    return None

def collect_status():
    """Collect node status."""
    print("  [STATUS] Fetching node status...")
    
    data = fetch_json(f'{BASE_URL}/status')
    if data:
        store_raw_event('qubic', 'status', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
            'endpoint': f'{BASE_URL}/status',
        })
        
        print(f"    Version: {data.get('version')}")
        print(f"    Peers: {data.get('numberOfConnectedPeers')}")
        
        return data
    return None

def collect_static_data():
    """Collect static registry data."""
    print("  [STATIC] Fetching static registry...")
    
    data = fetch_json(f'{STATIC_URL}/general/data/')
    if data:
        store_raw_event('qubic', 'static_registry', data, {
            'source_id': 'qubic-static',
            'source_type': 'rest',
            'endpoint': f'{STATIC_URL}/general/data/',
        })
        
        # Extract useful info
        if isinstance(data, dict):
            contracts = data.get('contracts', [])
            exchanges = data.get('exchanges', [])
            tokens = data.get('tokens', [])
            
            print(f"    Contracts: {len(contracts)}")
            print(f"    Exchanges: {len(exchanges)}")
            print(f"    Tokens: {len(tokens)}")
        
        return data
    return None

def collect_epoch_info():
    """Collect epoch information."""
    print("  [EPOCH] Fetching epoch info...")
    
    data = fetch_json(f'{BASE_URL}/epoch-info')
    if data:
        store_raw_event('qubic', 'epoch_info', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
            'endpoint': f'{BASE_URL}/epoch-info',
        })
        
        print(f"    Epoch: {data.get('epoch')}")
        print(f"    Start tick: {data.get('startTick')}")
        print(f"    End tick: {data.get('endTick')}")
        
        return data
    return None

def collect_contract_flows():
    """Collect recent contract flows."""
    print("  [CONTRACTS] Fetching contract data...")
    
    # Try to get contract state
    data = fetch_json(f'{BASE_URL}/contracts')
    if data:
        store_raw_event('qubic', 'contracts', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
            'endpoint': f'{BASE_URL}/contracts',
        })
        
        if isinstance(data, list):
            print(f"    Contracts: {len(data)}")
        elif isinstance(data, dict):
            print(f"    Contracts: {len(data.get('contracts', []))}")
        
        return data
    return None

def collect_all():
    """Collect all QUBIC data."""
    print(f"\n{'='*60}")
    print(f"QUBIC Data Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {}
    
    # Collect from each endpoint
    collectors = [
        ('tick', collect_tick_info),
        ('status', collect_status),
        ('static', collect_static_data),
        ('epoch', collect_epoch_info),
        ('contracts', collect_contract_flows),
    ]
    
    for name, collector in collectors:
        try:
            result = collector()
            results[name] = result is not None
            time.sleep(1)  # Rate limit
        except Exception as e:
            print(f"  Error in {name}: {e}")
            results[name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("QUBIC Collection Summary")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    return results

if __name__ == '__main__':
    collect_all()
