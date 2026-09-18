"""
PowPowPow — Raw Event Storage Layer
Immutable raw events before normalization.
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

WAREHOUSE_DIR = '/home/box/powpowpow/warehouse'
RAW_DIR = os.path.join(WAREHOUSE_DIR, 'raw')
NORMALIZED_DIR = os.path.join(WAREHOUSE_DIR, 'normalized')

# Create directories
for d in [RAW_DIR, NORMALIZED_DIR]:
    os.makedirs(d, exist_ok=True)
    for subdir in ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm', 'npt', 'qtc', 'market']:
        os.makedirs(os.path.join(d, subdir), exist_ok=True)

def store_raw_event(chain, event_type, payload, source_info=None):
    """
    Store raw event immutably.
    
    Args:
        chain: Chain identifier (qubic, prl, xmr, etc.)
        event_type: Type of event (tick, block, trade, depth, etc.)
        payload: Raw data payload (dict or list)
        source_info: Optional dict with source metadata
    """
    timestamp = datetime.now().isoformat()
    
    # Create source observation envelope
    observation = {
        'observed_at': timestamp,
        'chain_id': chain,
        'source_id': source_info.get('source_id', 'unknown') if source_info else 'unknown',
        'source_type': source_info.get('source_type', 'unknown') if source_info else 'unknown',
        'source_version': source_info.get('source_version', '1.0') if source_info else '1.0',
        'endpoint': source_info.get('endpoint', '') if source_info else '',
        'request_params': source_info.get('params', {}) if source_info else {},
        'raw_payload': payload,
        'payload_hash': hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest(),
        'ingest_version': '1.0',
    }
    
    # Write to raw storage
    chain_dir = os.path.join(RAW_DIR, chain)
    os.makedirs(chain_dir, exist_ok=True)
    
    filename = f"{event_type}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    filepath = os.path.join(chain_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(observation, f, indent=2, default=str)
    
    return filepath

def store_normalized(table_name, chain, data, timestamp=None):
    """
    Store normalized data in partitioned tables.
    
    Args:
        table_name: Table name (chain_snapshot, block, miner_economics, etc.)
        chain: Chain identifier
        data: Normalized data dict
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    table_dir = os.path.join(NORMALIZED_DIR, table_name)
    os.makedirs(table_dir, exist_ok=True)
    
    # Partition by date
    date_dir = os.path.join(table_dir, f"chain={chain}", f"date={timestamp:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)
    
    # Append to hourly partition
    hour_file = os.path.join(date_dir, f"hour={timestamp:%H}.jsonl")
    
    record = {
        'timestamp': timestamp.isoformat(),
        'chain': chain,
        **data
    }
    
    with open(hour_file, 'a') as f:
        f.write(json.dumps(record, default=str) + '\n')
    
    return hour_file

def read_normalized(table_name, chain=None, date=None):
    """Read normalized data from table."""
    table_dir = os.path.join(NORMALIZED_DIR, table_name)
    if not os.path.exists(table_dir):
        return []
    
    results = []
    
    if chain:
        chain_dirs = [os.path.join(table_dir, f"chain={chain}")]
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
    # Test storage
    print("Testing raw event storage...")
    
    test_payload = {
        'tick': 12345,
        'epoch': 100,
        'tx_count': 5,
    }
    
    filepath = store_raw_event('qubic', 'tick', test_payload, {
        'source_id': 'qubic-rpc',
        'source_type': 'rpc',
        'endpoint': 'https://rpc.qubic.org/v1/tick-info',
    })
    print(f"  Stored raw event: {filepath}")
    
    # Test normalized storage
    print("\nTesting normalized storage...")
    
    test_snapshot = {
        'height': 12345,
        'epoch': 100,
        'difficulty': 1000000,
        'hashrate': 500000,
    }
    
    hour_file = store_normalized('chain_snapshot', 'qubic', test_snapshot)
    print(f"  Stored normalized: {hour_file}")
    
    # Read back
    print("\nReading normalized data...")
    data = read_normalized('chain_snapshot', chain='qubic')
    print(f"  Found {len(data)} records")
    if data:
        print(f"  Latest: {data[-1]}")
    
    print("\nDone!")
