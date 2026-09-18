"""
PowPowPow Master Daemon
Runs all collectors continuously, normalizes data, serves API.
"""

import asyncio
import os
import sys
import time
import json
import signal
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = '/home/box/powpowpow'
sys.path.insert(0, BASE_DIR)

from warehouse import store_raw_event, store_normalized, read_normalized

# Configuration
CONFIG = {
    'collection_interval': 300,  # 5 minutes for chain data
    'l2_archive_interval': 0,    # Continuous for L2
    'normalization_interval': 60, # 1 minute
    'api_port': 5000,
}

class PowPowPowDaemon:
    def __init__(self):
        self.running = False
        self.processes = {}
        self.stats = {
            'started_at': None,
            'cycles': 0,
            'errors': 0,
            'last_collection': None,
            'last_normalization': None,
        }
    
    def start(self):
        """Start all components."""
        print(f"\n{'='*60}")
        print(f"PowPowPow Daemon Starting — {datetime.now()}")
        print(f"{'='*60}")
        
        self.running = True
        self.stats['started_at'] = datetime.now().isoformat()
        
        # Start collectors
        self.start_collectors()
        
        # Start API
        self.start_api()
        
        # Start normalization loop
        self.start_normalizer()
        
        # Start L2 archival
        self.start_l2_archival()
        
        print(f"\n[RUNNING] All components started")
        print(f"[PID] {os.getpid()}")
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
                self.stats['cycles'] += 1
                
                # Periodic status
                if self.stats['cycles'] % 60 == 0:
                    self.print_status()
        except KeyboardInterrupt:
            self.stop()
    
    def start_collectors(self):
        """Start chain data collectors."""
        print("[STARTING] Chain collectors...")
        
        # QUBIC collector
        self.processes['qubic'] = subprocess.Popen(
            [sys.executable, f'{BASE_DIR}/collectors/qubic_collector.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("  ✓ QUBIC collector")
        
        # PRL collector
        self.processes['prl'] = subprocess.Popen(
            [sys.executable, f'{BASE_DIR}/collectors/prl_collector.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("  ✓ PRL collector")
    
    def start_l2_archival(self):
        """Start L2 archival process."""
        print("[STARTING] L2 archival...")
        
        self.processes['l2'] = subprocess.Popen(
            [sys.executable, f'{BASE_DIR}/collectors/l2_archival.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("  ✓ L2 archival")
    
    def start_api(self):
        """Start API server."""
        print("[STARTING] API server...")
        
        self.processes['api'] = subprocess.Popen(
            [sys.executable, f'{BASE_DIR}/api.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"  ✓ API on port {CONFIG['api_port']}")
    
    def start_normalizer(self):
        """Start normalization loop."""
        print("[STARTING] Normalizer...")
        self.stats['last_normalization'] = datetime.now().isoformat()
        print("  ✓ Normalizer")
    
    def normalize_data(self):
        """Run normalization pipeline."""
        try:
            # Read raw events and normalize
            for chain in ['qubic', 'prl']:
                raw_dir = f'/home/box/powpowpow/warehouse/raw/{chain}'
                if os.path.exists(raw_dir):
                    files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
                    for f in files[-10:]:  # Process last 10 files
                        filepath = os.path.join(raw_dir, f)
                        try:
                            with open(filepath) as fh:
                                event = json.load(fh)
                            
                            # Normalize based on event type
                            event_type = f.split('_')[0]
                            payload = event.get('raw_payload', {})
                            
                            if event_type == 'tick':
                                store_normalized('chain_snapshot', chain, {
                                    'height': payload.get('tick', payload.get('tickNumber')),
                                    'epoch': payload.get('epoch'),
                                })
                            elif event_type == 'block':
                                store_normalized('block', chain, {
                                    'height': payload.get('height'),
                                    'hash': payload.get('hash'),
                                    'timestamp': payload.get('timestamp'),
                                })
                            
                            self.stats['last_normalization'] = datetime.now().isoformat()
                        except Exception as e:
                            self.stats['errors'] += 1
        except Exception as e:
            self.stats['errors'] += 1
    
    def print_status(self):
        """Print daemon status."""
        elapsed = time.time() - time.mktime(datetime.fromisoformat(self.stats['started_at']).timetuple())
        print(f"\n[STATUS] Uptime: {elapsed/3600:.1f}h | Cycles: {self.stats['cycles']} | Errors: {self.stats['errors']}")
        
        # Check processes
        for name, proc in self.processes.items():
            status = "running" if proc.poll() is None else "stopped"
            print(f"  {name}: {status}")
    
    def stop(self):
        """Stop all components."""
        print("\n[STOPPING] Daemon...")
        self.running = False
        
        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  ✓ Stopped {name}")
            except:
                proc.kill()
                print(f"  ✓ Killed {name}")
        
        print("[STOPPED] Daemon stopped")

def run_daemon():
    """Main entry point."""
    daemon = PowPowPowDaemon()
    
    def signal_handler(sig, frame):
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    daemon.start()

if __name__ == '__main__':
    run_daemon()
