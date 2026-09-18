"""
PRL (Pearl) Data Collector — Phase 1
Pulls from PearlTrack API and RPC.
"""

import json
import os
import requests
import time
from datetime import datetime
import sys
sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event, store_normalized

PEARLTRACK_API = 'https://pearltrack.io/api/v1'
PEARL_RPC = 'https://rpc.pearlresearch.ai'

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

def collect_network_stats():
    """Collect PRL network statistics."""
    print("  [NETWORK] Fetching network stats...")
    
    data = fetch_json(f'{PEARLTRACK_API}/network')
    if data:
        store_raw_event('prl', 'network_stats', data, {
            'source_id': 'pearltrack-api',
            'source_type': 'rest',
            'endpoint': f'{PEARLTRACK_API}/network',
        })
        
        # Normalize
        store_normalized('chain_snapshot', 'prl', {
            'height': data.get('height'),
            'hashrate': data.get('hashrate'),
            'difficulty': data.get('difficulty'),
            'block_reward': data.get('blockReward'),
            'circulating_supply': data.get('circulatingSupply'),
        })
        
        print(f"    Height: {data.get('height')}")
        print(f"    Hashrate: {data.get('hashrate')}")
        print(f"    Difficulty: {data.get('difficulty')}")
        print(f"    Block reward: {data.get('blockReward')}")
        
        return data
    return None

def collect_pools():
    """Collect mining pool data."""
    print("  [POOLS] Fetching pool data...")
    
    data = fetch_json(f'{PEARLTRACK_API}/pools')
    if data:
        store_raw_event('prl', 'pools', data, {
            'source_id': 'pearltrack-api',
            'source_type': 'rest',
            'endpoint': f'{PEARLTRACK_API}/pools',
        })
        
        if isinstance(data, list):
            print(f"    Pools: {len(data)}")
            for pool in data[:5]:
                print(f"      {pool.get('name')}: {pool.get('share')}% - {pool.get('hashrate')}")
        elif isinstance(data, dict):
            pools = data.get('pools', [])
            print(f"    Pools: {len(pools)}")
        
        return data
    return None

def collect_recent_blocks():
    """Collect recent blocks."""
    print("  [BLOCKS] Fetching recent blocks...")
    
    data = fetch_json(f'{PEARLTRACK_API}/blocks', params={'limit': 10})
    if data:
        store_raw_event('prl', 'recent_blocks', data, {
            'source_id': 'pearltrack-api',
            'source_type': 'rest',
            'endpoint': f'{PEARLTRACK_API}/blocks',
        })
        
        blocks = data if isinstance(data, list) else data.get('blocks', [])
        print(f"    Blocks: {len(blocks)}")
        
        # Store each block
        for block in blocks[:5]:
            store_normalized('block', 'prl', {
                'height': block.get('height'),
                'hash': block.get('hash'),
                'timestamp': block.get('timestamp'),
                'difficulty': block.get('difficulty'),
                'reward': block.get('reward'),
                'miner_address': block.get('miner'),
                'tx_count': block.get('txCount'),
            })
        
        return data
    return None

def collect_transfers():
    """Collect recent transfers for miner flow analysis."""
    print("  [TRANSFERS] Fetching recent transfers...")
    
    data = fetch_json(f'{PEARLTRACK_API}/transfers', params={'limit': 100})
    if data:
        store_raw_event('prl', 'transfers', data, {
            'source_id': 'pearltrack-api',
            'source_type': 'rest',
            'endpoint': f'{PEARLTRACK_API}/transfers',
        })
        
        transfers = data if isinstance(data, list) else data.get('transfers', [])
        print(f"    Transfers: {len(transfers)}")
        
        # Analyze for miner flows
        pool_payouts = [t for t in transfers if t.get('type') == 'poolPayout']
        large_transfers = [t for t in transfers if float(t.get('amount', 0)) > 1000]
        
        print(f"    Pool payouts: {len(pool_payouts)}")
        print(f"    Large transfers (>1000 PRL): {len(large_transfers)}")
        
        # Store miner flow data
        for transfer in transfers:
            store_normalized('miner_flow', 'prl', {
                'txid': transfer.get('txid'),
                'source_pool': transfer.get('sourcePool'),
                'miner_address': transfer.get('minerAddress'),
                'destination': transfer.get('destination'),
                'amount_prl': transfer.get('amount'),
                'classification': transfer.get('type'),
            })
        
        return data
    return None

def collect_addresses():
    """Collect top addresses for exchange tracking."""
    print("  [ADDRESSES] Fetching top addresses...")
    
    data = fetch_json(f'{PEARLTRACK_API}/addresses', params={'limit': 50})
    if data:
        store_raw_event('prl', 'addresses', data, {
            'source_id': 'pearltrack-api',
            'source_type': 'rest',
            'endpoint': f'{PEARLTRACK_API}/addresses',
        })
        
        addresses = data if isinstance(data, list) else data.get('addresses', [])
        print(f"    Addresses: {len(addresses)}")
        
        # Identify exchange addresses
        exchanges = [a for a in addresses if a.get('label') and 'exchange' in a.get('label', '').lower()]
        print(f"    Exchange-labeled: {len(exchanges)}")
        
        return data
    return None

def collect_all():
    """Collect all PRL data."""
    print(f"\n{'='*60}")
    print(f"PRL (Pearl) Data Collection — {datetime.now()}")
    print(f"{'='*60}")
    
    results = {}
    
    collectors = [
        ('network', collect_network_stats),
        ('pools', collect_pools),
        ('blocks', collect_recent_blocks),
        ('transfers', collect_transfers),
        ('addresses', collect_addresses),
    ]
    
    for name, collector in collectors:
        try:
            result = collector()
            results[name] = result is not None
            time.sleep(1)
        except Exception as e:
            print(f"  Error in {name}: {e}")
            results[name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("PRL Collection Summary")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    return results

if __name__ == '__main__':
    collect_all()
