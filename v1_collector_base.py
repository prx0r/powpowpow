"""
V1 Collector Interface
Every chain collector must implement this.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
import hashlib

class V1Collector(ABC):
    """Base class for all V1 chain collectors."""
    
    def __init__(self, chain_id: str, data_dir: str):
        self.chain_id = chain_id
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    @abstractmethod
    def collect_price(self) -> Optional[Dict]:
        """Collect current price from exchange."""
        pass
    
    @abstractmethod
    def collect_network(self) -> Optional[Dict]:
        """Collect network stats (hashrate, difficulty, etc)."""
        pass
    
    @abstractmethod
    def collect_hardware_benchmarks(self) -> list:
        """Collect known hardware benchmarks."""
        pass
    
    def store_raw(self, source_id: str, source_type: str, endpoint: str, payload: Any):
        """Store raw event."""
        timestamp = datetime.now().isoformat()
        
        event = {
            'observed_at': timestamp,
            'chain_id': self.chain_id,
            'source_id': source_id,
            'source_type': source_type,
            'source_version': '1.0',
            'endpoint': endpoint,
            'raw_payload': payload,
            'payload_hash': hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest(),
            'ingest_version': '1.0',
        }
        
        filename = f"{source_id}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        filepath = os.path.join(self.data_dir, 'raw', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(event, f, indent=2, default=str)
        
        return filepath
    
    def store_normalized(self, table: str, data: Dict):
        """Store normalized data."""
        timestamp = datetime.now()
        
        record = {
            'timestamp': timestamp.isoformat(),
            'chain': self.chain_id,
            **data
        }
        
        table_dir = os.path.join(self.data_dir, 'normalized', table)
        os.makedirs(table_dir, exist_ok=True)
        
        hour_file = os.path.join(table_dir, f"{timestamp:%Y%m%d_%H}.jsonl")
        with open(hour_file, 'a') as f:
            f.write(json.dumps(record, default=str) + '\n')
        
        return hour_file
    
    def collect_all(self) -> Dict:
        """Run all collectors and return results."""
        print(f"\n{'='*60}")
        print(f"{self.chain_id} Collection — {datetime.now()}")
        print(f"{'='*60}")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'chain': self.chain_id,
        }
        
        # Price
        try:
            results['price'] = self.collect_price()
            if results['price']:
                price_val = results['price'].get('usd', 'N/A') if isinstance(results['price'], dict) else results['price']
                print(f"  Price: ${price_val}")
        except Exception as e:
            print(f"  Price error: {e}")
            results['price'] = None
        
        # Network
        try:
            results['network'] = self.collect_network()
            if results['network']:
                print(f"  Network: {list(results['network'].keys())[:3]}")
        except Exception as e:
            print(f"  Network error: {e}")
            results['network'] = None
        
        # Benchmarks
        try:
            results['benchmarks'] = self.collect_hardware_benchmarks()
            if results['benchmarks']:
                print(f"  Benchmarks: {len(results['benchmarks'])} hardware types")
        except Exception as e:
            print(f"  Benchmark error: {e}")
            results['benchmarks'] = []
        
        # Store raw
        self.store_raw(
            source_id=f'{self.chain_id}-collector',
            source_type='pipeline',
            endpoint='collect_all',
            payload=results
        )
        
        # Save
        filepath = os.path.join(self.data_dir, f'{self.chain_id}_data.json')
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"  Saved: {filepath}")
        
        return results
