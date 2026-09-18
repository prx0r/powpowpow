"""
PowPowPow V1 Data Pipeline Architecture

Flow:
  Source APIs → Raw Events → Normalized Tables → Live Cards → API/Exports

Every observation carries:
  observed_at | chain_id | source_id | source_type | raw_payload | payload_hash
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, '/home/box/powpowpow')

BASE_DIR = '/home/box/powpowpow'
WAREHOUSE_DIR = os.path.join(BASE_DIR, 'warehouse')
RAW_DIR = os.path.join(WAREHOUSE_DIR, 'raw')
NORMALIZED_DIR = os.path.join(WAREHOUSE_DIR, 'normalized')

# Create directories
for d in [RAW_DIR, NORMALIZED_DIR]:
    os.makedirs(d, exist_ok=True)
    for chain in ['prl', 'qubic', 'quan', 'xmr', 'kas', 'clore', 'akt', 'nos']:
        os.makedirs(os.path.join(d, chain), exist_ok=True)

def store_raw(chain_id, source_id, source_type, endpoint, payload, node_height=None, node_tip_hash=None):
    """
    Store raw event immutably.
    
    This is the foundation of the moat. Raw data cannot be reconstructed later.
    """
    timestamp = datetime.now().isoformat()
    
    # Create envelope
    event = {
        'observed_at': timestamp,
        'chain_id': chain_id,
        'source_id': source_id,
        'source_type': source_type,
        'source_version': '1.0',
        'endpoint': endpoint,
        'request_params': {},
        'raw_payload': payload,
        'payload_hash': hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest(),
        'node_height': node_height,
        'node_tip_hash': node_tip_hash,
        'ingest_version': '1.0',
    }
    
    # Write to raw storage (append-only)
    chain_dir = os.path.join(RAW_DIR, chain_id)
    os.makedirs(chain_dir, exist_ok=True)
    
    filename = f"{source_id}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    filepath = os.path.join(chain_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(event, f, indent=2, default=str)
    
    return filepath

def store_normalized(table_name, chain_id, data):
    """
    Store normalized data in partitioned tables.
    
    Partitioned by chain/date for efficient querying.
    """
    timestamp = datetime.now()
    
    table_dir = os.path.join(NORMALIZED_DIR, table_name)
    os.makedirs(table_dir, exist_ok=True)
    
    # Partition by chain and date
    chain_dir = os.path.join(table_dir, f"chain={chain_id}")
    date_dir = os.path.join(chain_dir, f"date={timestamp:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)
    
    # Append to hourly partition
    hour_file = os.path.join(date_dir, f"hour={timestamp:%H}.jsonl")
    
    record = {
        'timestamp': timestamp.isoformat(),
        'chain': chain_id,
        **data
    }
    
    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')
    
    return hour_file

def read_normalized(table_name, chain_id=None, date=None):
    """Read normalized data."""
    table_dir = os.path.join(NORMALIZED_DIR, table_name)
    if not os.path.exists(table_dir):
        return []
    
    results = []
    
    if chain_id:
        chain_dirs = [os.path.join(table_dir, f"chain={chain_id}")]
    else:
        chain_dirs = [os.path.join(table_dir, d) for d in os.listdir(table_dir) if d.startswith('chain=')]
    
    for chain_dir in chain_dirs:
        if not os.path.exists(chain_dir):
            continue
        
        if date:
            date_dirs = [os.path.join(chain_dir, f"date={date}")]
        else:
            date_dirs = [os.path.join(chain_dir, d) for d in os.listdir(chain_dir) if d.startswith('date=')]
        
        for date_dir in date_dirs:
            if not os.path.exists(date_dir):
                continue
            
            for hour_file in sorted(os.listdir(date_dir)):
                if hour_file.endswith('.jsonl'):
                    with open(os.path.join(date_dir, hour_file)) as f:
                        for line in f:
                            if line.strip():
                                results.append(json.loads(line))
    
    return results

if __name__ == '__main__':
    # Test pipeline
    print("Testing V1 Pipeline...")
    
    # Store raw event
    filepath = store_raw(
        chain_id='prl',
        source_id='prlscan-api',
        source_type='rest',
        endpoint='https://prlscan.com/api/v1/network',
        payload={'hashrate': '21.9 EH/s', 'difficulty': '19.99M'}
    )
    print(f"  Raw event: {filepath}")
    
    # Store normalized
    hour_file = store_normalized('chain_snapshot', 'prl', {
        'height': 100855,
        'hashrate': 21.9e18,
        'difficulty': 19.99e6,
    })
    print(f"  Normalized: {hour_file}")
    
    # Read back
    data = read_normalized('chain_snapshot', chain_id='prl')
    print(f"  Records: {len(data)}")
    if data:
        print(f"  Latest: {data[-1]}")
    
    print("\nPipeline test complete!")
