"""
Monitoring & Health Checks
Tracks system status and data freshness.
"""

import json
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WAREHOUSE_DIR = os.path.join(BASE_DIR, 'warehouse')
CHAINS_DIR = os.path.join(BASE_DIR, 'chains')

def check_data_freshness():
    """Check how fresh data is for each chain."""
    print(f"\n{'='*60}")
    print(f"Data Freshness Check — {datetime.now()}")
    print(f"{'='*60}")
    
    chains = ['qubic', 'prl', 'nock', 'xmr', 'gnk', 'tsc', 'xel', 'xtm']
    
    for chain in chains:
        raw_dir = os.path.join(WAREHOUSE_DIR, 'raw', chain)
        if os.path.exists(raw_dir):
            files = [f for f in os.listdir(raw_dir) if f.endswith('.json') and 'processed' not in f]
            if files:
                # Get most recent file
                most_recent = max(files, key=lambda f: os.path.getmtime(os.path.join(raw_dir, f)))
                mtime = os.path.getmtime(os.path.join(raw_dir, most_recent))
                age = datetime.now() - datetime.fromtimestamp(mtime)
                
                status = "FRESH" if age < timedelta(minutes=10) else "STALE"
                print(f"  {chain:8} | {len(files):3} raw events | Latest: {age.total_seconds()/60:.0f}m ago | {status}")
            else:
                print(f"  {chain:8} | No raw events")
        else:
            print(f"  {chain:8} | No data directory")
    
    # Check normalized data
    print(f"\n  Normalized tables:")
    normalized_dir = os.path.join(WAREHOUSE_DIR, 'normalized')
    if os.path.exists(normalized_dir):
        for table in sorted(os.listdir(normalized_dir)):
            table_dir = os.path.join(normalized_dir, table)
            if os.path.isdir(table_dir):
                total_records = 0
                for chain_dir in os.listdir(table_dir):
                    if chain_dir.startswith('chain='):
                        for date_dir in os.listdir(os.path.join(table_dir, chain_dir)):
                            if date_dir.startswith('date='):
                                date_path = os.path.join(table_dir, chain_dir, date_dir)
                                for hour_file in os.listdir(date_path):
                                    if hour_file.endswith('.jsonl'):
                                        with open(os.path.join(date_path, hour_file)) as f:
                                            total_records += sum(1 for _ in f)
                
                print(f"    {table:25} | {total_records:6} records")

def check_api_health():
    """Check if API is running."""
    print(f"\n  API Health:")
    try:
        import requests
        resp = requests.get('http://localhost:5000/api/v1/health', timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            print(f"    Status: {data.get('status')}")
            print(f"    Chains tracked: {data.get('chains_tracked')}")
        else:
            print(f"    Status: Error {resp.status_code}")
    except:
        print(f"    Status: Not running")

def check_collector_health():
    """Check if collectors are running."""
    print(f"\n  Collector Health:")
    
    pid_file = os.path.join(BASE_DIR, 'daemon.pid')
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"    Daemon: Running (PID {pid})")
        except:
            print(f"    Daemon: Not running (stale PID {pid})")
    else:
        print(f"    Daemon: No PID file")

def health_check():
    """Run all health checks."""
    check_data_freshness()
    check_api_health()
    check_collector_health()

if __name__ == '__main__':
    health_check()
