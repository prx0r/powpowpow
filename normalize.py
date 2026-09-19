"""
Normalization Pipeline
Converts raw events to normalized tables.
"""

import json
import os
import glob
from datetime import datetime
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from warehouse import store_normalized, read_normalized

RAW_DIR = os.path.join(BASE_DIR, 'warehouse', 'raw')
NORMALIZED_DIR = os.path.join(BASE_DIR, 'warehouse', 'normalized')

def normalize_chain_snapshots():
    """Normalize chain snapshot data from raw events."""
    print("[NORMALIZE] Chain snapshots...")
    
    for chain in ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'xel', 'xtm']:
        raw_dir = os.path.join(RAW_DIR, chain)
        if not os.path.exists(raw_dir):
            continue
        
        # Process tick/status files
        for pattern in ['tick_info_*.json', 'status_*.json', 'network_stats_*.json']:
            files = sorted(glob.glob(os.path.join(raw_dir, pattern)))
            
            for f in files[-5:]:  # Last 5 files
                try:
                    with open(f) as fh:
                        event = json.load(fh)
                    
                    payload = event.get('raw_payload', {})
                    observed_at = event.get('observed_at')
                    
                    if 'tick' in pattern:
                        store_normalized('chain_snapshot', chain, {
                            'height': payload.get('tick', payload.get('tickNumber', payload.get('height'))),
                            'epoch': payload.get('epoch'),
                            'tx_count': payload.get('txCount', payload.get('tx_count')),
                        })
                    elif 'status' in pattern:
                        store_normalized('chain_snapshot', chain, {
                            'peer_count': payload.get('numberOfConnectedPeers', payload.get('peers')),
                            'version': payload.get('version'),
                        })
                    elif 'network' in pattern:
                        store_normalized('chain_snapshot', chain, {
                            'hashrate': payload.get('hashrate'),
                            'difficulty': payload.get('difficulty'),
                            'block_reward': payload.get('blockReward'),
                            'circulating_supply': payload.get('circulatingSupply'),
                        })
                    
                    # Move processed file
                    processed_dir = os.path.join(raw_dir, 'processed')
                    os.makedirs(processed_dir, exist_ok=True)
                    os.rename(f, os.path.join(processed_dir, os.path.basename(f)))
                    
                except Exception as e:
                    print(f"  Error processing {f}: {e}")

def normalize_blocks():
    """Normalize block data from raw events."""
    print("[NORMALIZE] Blocks...")
    
    for chain in ['prl', 'xmr', 'xel', 'xtm']:
        raw_dir = os.path.join(RAW_DIR, chain)
        if not os.path.exists(raw_dir):
            continue
        
        files = sorted(glob.glob(os.path.join(raw_dir, 'recent_blocks_*.json')))
        
        for f in files[-3:]:
            try:
                with open(f) as fh:
                    event = json.load(fh)
                
                payload = event.get('raw_payload', {})
                blocks = payload if isinstance(payload, list) else payload.get('blocks', [])
                
                for block in blocks:
                    store_normalized('block', chain, {
                        'height': block.get('height'),
                        'hash': block.get('hash'),
                        'timestamp': block.get('timestamp'),
                        'difficulty': block.get('difficulty'),
                        'reward': block.get('reward'),
                        'miner_address': block.get('miner'),
                        'tx_count': block.get('txCount'),
                    })
                
                processed_dir = os.path.join(raw_dir, 'processed')
                os.makedirs(processed_dir, exist_ok=True)
                os.rename(f, os.path.join(processed_dir, os.path.basename(f)))
                
            except Exception as e:
                print(f"  Error processing {f}: {e}")

def normalize_miner_flows():
    """Normalize miner flow data from PRL transfers."""
    print("[NORMALIZE] Miner flows...")
    
    raw_dir = os.path.join(RAW_DIR, 'prl')
    if not os.path.exists(raw_dir):
        return
    
    files = sorted(glob.glob(os.path.join(raw_dir, 'transfers_*.json')))
    
    for f in files[-3:]:
        try:
            with open(f) as fh:
                event = json.load(fh)
            
            payload = event.get('raw_payload', {})
            transfers = payload if isinstance(payload, list) else payload.get('transfers', [])
            
            for transfer in transfers:
                store_normalized('miner_flow', 'prl', {
                    'txid': transfer.get('txid'),
                    'source_pool': transfer.get('sourcePool'),
                    'miner_address': transfer.get('minerAddress'),
                    'destination': transfer.get('destination'),
                    'amount_prl': transfer.get('amount'),
                    'classification': transfer.get('type'),
                })
            
            processed_dir = os.path.join(raw_dir, 'processed')
            os.makedirs(processed_dir, exist_ok=True)
            os.rename(f, os.path.join(processed_dir, os.path.basename(f)))
            
        except Exception as e:
            print(f"  Error processing {f}: {e}")

def normalize_all():
    """Run all normalization."""
    print(f"\n{'='*60}")
    print(f"Normalization Pipeline — {datetime.now()}")
    print(f"{'='*60}")
    
    normalize_chain_snapshots()
    normalize_blocks()
    normalize_miner_flows()
    
    # Count normalized records
    total_records = 0
    for table in os.listdir(NORMALIZED_DIR):
        table_dir = os.path.join(NORMALIZED_DIR, table)
        if os.path.isdir(table_dir):
            for chain_dir in os.listdir(table_dir):
                if chain_dir.startswith('chain='):
                    for date_dir in os.listdir(os.path.join(table_dir, chain_dir)):
                        if date_dir.startswith('date='):
                            date_path = os.path.join(table_dir, chain_dir, date_dir)
                            for hour_file in os.listdir(date_path):
                                if hour_file.endswith('.jsonl'):
                                    with open(os.path.join(date_path, hour_file)) as f:
                                        total_records += sum(1 for _ in f)
    
    print(f"\n[DONE] Total normalized records: {total_records}")

if __name__ == '__main__':
    normalize_all()
