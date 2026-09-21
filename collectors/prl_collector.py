"""
PRL (Pearl) Data Collector — Phase 1
Source hierarchy (PR1 item 5): own pearld = canonical chain truth,
PearlTrack = derived/enrichment/labels only. Until pearld is wired,
all PearlTrack-sourced rows carry source_role=derived + classification
provenance, never canonical.
"""

import json
import os
import time
from datetime import datetime, timezone
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from core import fetch_json, store_normalized, utcnow

PEARLTRACK_API = 'https://pearltrack.io/api/v1'
PEARL_RPC = 'https://rpc.pearlresearch.ai'

CLASSIFICATION_SOURCE = 'pearltrack-api'
CLASSIFICATION_VERSION = 'pearltrack-v1-labels'
CLASSIFICATION_CONFIDENCE = 'medium-unverified'  # our labels until pearld cross-check

def collect_network_stats():
    """Collect PRL network statistics (PearlTrack = derived until pearld lands)."""
    print("  [NETWORK] Fetching network stats (auto-archiving)...")
    data = fetch_json(f'{PEARLTRACK_API}/network', source_id='pearltrack-api',
                      chain_id='prl')
    if data:
        
        # Normalize (derived role — not canonical chain truth)
        store_normalized('chain_snapshot', 'prl', {
            'height': data.get('height'),
            'hashrate': data.get('hashrate'),
            'difficulty': data.get('difficulty'),
            'block_reward': data.get('blockReward'),
            'circulating_supply': data.get('circulatingSupply'),
            'source_role': 'derived',
            'source_id': 'pearltrack-api',
        })
        
        print(f"    Height: {data.get('height')}")
        print(f"    Hashrate: {data.get('hashrate')}")
        print(f"    Difficulty: {data.get('difficulty')}")
        print(f"    Block reward: {data.get('blockReward')}")
        
        return data
    return None

def collect_pools():
    """Collect mining pool data (auto-archiving)."""
    print("  [POOLS] Fetching pool data...")
    data = fetch_json(f'{PEARLTRACK_API}/pools', source_id='pearltrack-api',
                      chain_id='prl')
    if data:
        
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
    """Collect recent blocks (auto-archiving)."""
    print("  [BLOCKS] Fetching recent blocks...")
    data = fetch_json(f'{PEARLTRACK_API}/blocks', params={'limit': 10},
                      source_id='pearltrack-api', chain_id='prl')
    if data:
        
        blocks = data if isinstance(data, list) else data.get('blocks', [])
        print(f"    Blocks: {len(blocks)}")
        
        # Store each block (derived until pearld canonical)
        for block in blocks[:5]:
            store_normalized('block', 'prl', {
                'height': block.get('height'),
                'hash': block.get('hash'),
                'timestamp': block.get('timestamp'),
                'difficulty': block.get('difficulty'),
                'reward': block.get('reward'),
                'miner_address': block.get('miner'),
                'tx_count': block.get('txCount'),
                'source_role': 'derived',
                'classification_source': CLASSIFICATION_SOURCE,
            })
        
        return data
    return None

def collect_transfers():
    """Collect recent transfers for miner flow analysis (labels = enrichment)."""
    print("  [TRANSFERS] Fetching recent transfers...")
    data = fetch_json(f'{PEARLTRACK_API}/transfers', params={'limit': 100},
                      source_id='pearltrack-api', chain_id='prl')
    if data:
        
        transfers = data if isinstance(data, list) else data.get('transfers', [])
        print(f"    Transfers: {len(transfers)}")
        pool_payouts = [t for t in transfers if t.get('type') == 'poolPayout']
        print(f"    Pool payouts (PearlTrack label): {len(pool_payouts)}")
        
        # Store miner flow data with classification provenance (PR1 item 5)
        for transfer in transfers:
            try:
                amt = float(transfer.get('amount', 0) or 0)
            except (TypeError, ValueError):
                amt = 0
            store_normalized('miner_flow', 'prl', {
                'txid': transfer.get('txid'),
                'source_pool': transfer.get('sourcePool'),
                'miner_address': transfer.get('minerAddress'),
                'destination': transfer.get('destination'),
                'amount_prl': transfer.get('amount'),
                'classification': transfer.get('type'),
                'classification_source': CLASSIFICATION_SOURCE,
                'classification_version': CLASSIFICATION_VERSION,
                'classification_confidence': CLASSIFICATION_CONFIDENCE,
                'source_role': 'derived',
            })
        
        return data
    return None

def collect_addresses():
    """Collect top addresses for exchange tracking (labels only)."""
    print("  [ADDRESSES] Fetching top addresses...")
    data = fetch_json(f'{PEARLTRACK_API}/addresses', params={'limit': 50},
                      source_id='pearltrack-api', chain_id='prl')
    if data:
        
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
    print(f"PRL (Pearl) Data Collection — {utcnow()}")
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
