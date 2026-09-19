"""
QUBIC Data Collector — Phase 1
Pulls from official Qubic RPC and static registry.
"""

import json
import os
import time
from datetime import datetime, timezone
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from core import fetch_json, store_normalized, utcnow

BASE_URL = 'https://rpc.qubic.org/v1'
STATIC_URL = 'https://static.qubic.org/v1'


def collect_tick_info():
    """Collect current tick information."""
    print("  [TICK] Fetching tick info...")
    
    data = fetch_json(f'{BASE_URL}/tick-info', source_id='qubic-rpc', chain_id='qubic')
    if data:
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
    
    data = fetch_json(f'{BASE_URL}/status', source_id='qubic-rpc', chain_id='qubic')
    if data:
        
        print(f"    Version: {data.get('version')}")
        print(f"    Peers: {data.get('numberOfConnectedPeers')}")
        
        return data
    return None

def collect_static_data():
    """Collect static registry data."""
    print("  [STATIC] Fetching static registry...")
    
    data = fetch_json(f'{STATIC_URL}/general/data/', source_id='qubic-static', chain_id='qubic')
    if data:
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
    
    data = fetch_json(f'{BASE_URL}/epoch-info', source_id='qubic-rpc', chain_id='qubic')
    if data:
        
        print(f"    Epoch: {data.get('epoch')}")
        print(f"    Start tick: {data.get('startTick')}")
        print(f"    End tick: {data.get('endTick')}")
        
        return data
    return None

def collect_contract_flows():
    """Collect recent contract flows."""
    print("  [CONTRACTS] Fetching contract data...")
    
    # Try to get contract state
    data = fetch_json(f'{BASE_URL}/contracts', source_id='qubic-rpc', chain_id='qubic')
    if data:
        
        if isinstance(data, list):
            print(f"    Contracts: {len(data)}")
        elif isinstance(data, dict):
            print(f"    Contracts: {len(data.get('contracts', []))}")
        
        return data
    return None

def collect_all():
    """Collect all QUBIC data."""
    print(f"\n{'='*60}")
    print(f"QUBIC Data Collection — {utcnow()}")
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
