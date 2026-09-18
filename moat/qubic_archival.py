"""
QUBIC Epoch/Computor Archival System
Builds complete epoch-by-epoch economic history.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys

sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event, store_normalized

DATA_DIR = '/home/box/powpowpow/moat/qubic'
os.makedirs(DATA_DIR, exist_ok=True)

RPC_URL = 'https://rpc.qubic.org/v1'
STATIC_URL = 'https://static.qubic.org/v1'

def fetch_json(url, params=None, timeout=15):
    try:
        resp = requests.get(url, params=params, headers={
            'User-Agent': 'PowPowPow/1.0',
            'Accept': 'application/json'
        }, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        pass
    return None

def archive_tick_info():
    """Archive current tick state."""
    print("  [TICK] Archiving tick info...")
    
    data = fetch_json(f'{RPC_URL}/tick-info')
    if data:
        store_raw_event('qubic', 'tick_archive', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
        })
        
        # Extract key fields
        tick = data.get('tick', data)
        archive = {
            'timestamp': datetime.now().isoformat(),
            'tick': tick.get('tick', tick.get('tickNumber')),
            'epoch': tick.get('epoch'),
            'hash': tick.get('hash'),
            'tx_count': tick.get('txCount'),
            'validity': tick.get('validity'),
        }
        
        # Save to moat directory
        archive_file = os.path.join(DATA_DIR, f'tick_{archive["tick"]}.json')
        with open(archive_file, 'w') as f:
            json.dump(archive, f, indent=2)
        
        print(f"    Tick: {archive['tick']}, Epoch: {archive['epoch']}")
        return archive
    return None

def archive_epoch_info():
    """Archive epoch information."""
    print("  [EPOCH] Archiving epoch info...")
    
    data = fetch_json(f'{RPC_URL}/epoch-info')
    if data:
        store_raw_event('qubic', 'epoch_archive', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
        })
        
        archive = {
            'timestamp': datetime.now().isoformat(),
            'epoch': data.get('epoch'),
            'start_tick': data.get('startTick'),
            'end_tick': data.get('endTick'),
            'computors': data.get('numberOfComputors'),
        }
        
        archive_file = os.path.join(DATA_DIR, f'epoch_{archive["epoch"]}.json')
        with open(archive_file, 'w') as f:
            json.dump(archive, f, indent=2)
        
        print(f"    Epoch: {archive['epoch']}, Computors: {archive['computors']}")
        return archive
    return None

def archive_static_registry():
    """Archive static data registry (contracts, exchanges, tokens)."""
    print("  [STATIC] Archiving static registry...")
    
    data = fetch_json(f'{STATIC_URL}/general/data/')
    if data:
        store_raw_event('qubic', 'static_archive', data, {
            'source_id': 'qubic-static',
            'source_type': 'rest',
        })
        
        archive = {
            'timestamp': datetime.now().isoformat(),
            'contracts': len(data.get('contracts', [])),
            'exchanges': len(data.get('exchanges', [])),
            'tokens': len(data.get('tokens', [])),
            'raw': data,
        }
        
        archive_file = os.path.join(DATA_DIR, f'static_{datetime.now():%Y%m%d}.json')
        with open(archive_file, 'w') as f:
            json.dump(archive, f, indent=2, default=str)
        
        print(f"    Contracts: {archive['contracts']}, Exchanges: {archive['exchanges']}")
        return archive
    return None

def archive_node_status():
    """Archive node status."""
    print("  [STATUS] Archiving node status...")
    
    data = fetch_json(f'{RPC_URL}/status')
    if data:
        store_raw_event('qubic', 'status_archive', data, {
            'source_id': 'qubic-rpc',
            'source_type': 'rpc',
        })
        
        archive = {
            'timestamp': datetime.now().isoformat(),
            'version': data.get('version'),
            'peers': data.get('numberOfConnectedPeers'),
            'processing': data.get('latestEpochTransitionInfo'),
        }
        
        archive_file = os.path.join(DATA_DIR, f'status_{datetime.now():%Y%m%d_%H}.json')
        with open(archive_file, 'w') as f:
            json.dump(archive, f, indent=2)
        
        print(f"    Version: {archive['version']}, Peers: {archive['peers']}")
        return archive
    return None

def archive_all():
    """Run all QUBIC archival."""
    print(f"\n{'='*60}")
    print(f"QUBIC Epoch Archival — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {}
    
    collectors = [
        ('tick', archive_tick_info),
        ('epoch', archive_epoch_info),
        ('static', archive_static_registry),
        ('status', archive_node_status),
    ]
    
    for name, collector in collectors:
        try:
            result = collector()
            results[name] = result is not None
            time.sleep(1)
        except Exception as e:
            print(f"  Error: {e}")
            results[name] = False
    
    # Save archive index
    index_file = os.path.join(DATA_DIR, 'archive_index.json')
    with open(index_file, 'w') as f:
        json.dump({
            'last_archive': datetime.now().isoformat(),
            'results': results,
        }, f, indent=2)
    
    print(f"\n[INDEX] {index_file}")
    return results

if __name__ == '__main__':
    archive_all()
