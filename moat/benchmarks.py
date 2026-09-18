"""
Hardware Benchmark Registry
Universal table for chain profitability analysis.
"""

import json
import os
from datetime import datetime
import sys

DATA_DIR = '/home/box/powpowpow/moat/benchmarks'
os.makedirs(DATA_DIR, exist_ok=True)

# Known hardware benchmarks (from public sources)
HARDWARE_DB = {
    'XMR': {
        'RandomX': {
            'cpu': [
                {'name': 'AMD Ryzen 9 7950X', 'hashrate': 22000, 'power': 170, 'cost': 600, 'cores': 16},
                {'name': 'AMD Ryzen 9 5950X', 'hashrate': 18000, 'power': 105, 'cost': 450, 'cores': 16},
                {'name': 'AMD Ryzen 7 7800X3D', 'hashrate': 15000, 'power': 120, 'cost': 400, 'cores': 8},
                {'name': 'Intel i9-13900K', 'hashrate': 14000, 'power': 253, 'cost': 550, 'cores': 24},
                {'name': 'AMD EPYC 7763', 'hashrate': 45000, 'power': 280, 'cost': 3000, 'cores': 64},
            ],
        },
    },
    'PRL': {
        'PearlHash': {
            'gpu': [
                {'name': 'NVIDIA RTX 4090', 'hashrate': 250e12, 'power': 450, 'cost': 2000, 'vram': 24},
                {'name': 'NVIDIA RTX 4080 Super', 'hashrate': 203e12, 'power': 270, 'cost': 1250, 'vram': 16},
                {'name': 'NVIDIA CMP 170HX', 'hashrate': 175e12, 'power': 240, 'cost': 4000, 'vram': 8},
                {'name': 'NVIDIA H100', 'hashrate': 3000e12, 'power': 700, 'cost': 30000, 'vram': 80},
                {'name': 'NVIDIA H200', 'hashrate': 4000e12, 'power': 700, 'cost': 40000, 'vram': 141},
            ],
        },
    },
    'XEL': {
        'XelisHash': {
            'gpu': [
                {'name': 'NVIDIA RTX 4080 Super', 'hashrate': 10100, 'power': 145, 'cost': 1250, 'vram': 16},
                {'name': 'NVIDIA RTX 4070', 'hashrate': 7500, 'power': 100, 'cost': 600, 'vram': 12},
                {'name': 'NVIDIA RTX 3080', 'hashrate': 6000, 'power': 120, 'cost': 500, 'vram': 10},
            ],
            'cpu': [
                {'name': 'AMD Ryzen 9 7950X', 'hashrate': 500, 'power': 170, 'cost': 600, 'cores': 16},
                {'name': 'AMD Ryzen 7 7800X3D', 'hashrate': 350, 'power': 120, 'cost': 400, 'cores': 8},
            ],
        },
    },
    'XTM': {
        'RandomX': {
            'cpu': [
                {'name': 'AMD Ryzen 9 7950X', 'hashrate': 22000, 'power': 170, 'cost': 600, 'cores': 16},
                {'name': 'AMD Ryzen 7 7800X3D', 'hashrate': 15000, 'power': 120, 'cost': 400, 'cores': 8},
            ],
        },
    },
    'NOCK': {
        'ZK-STARK': {
            'cpu': [
                {'name': 'AMD Ryzen 9 7950X', 'hashrate': 100, 'power': 170, 'cost': 600, 'cores': 16},
            ],
            'gpu': [
                {'name': 'NVIDIA RTX 4090', 'hashrate': 500, 'power': 450, 'cost': 2000, 'vram': 24},
            ],
        },
    },
}

# Electricity cost default
ELECTRICITY_DEFAULT = 0.10  # $/kWh

def calculate_profitability(chain, algo, device_type, electricity=ELECTRICITY_DEFAULT):
    """Calculate profitability for hardware on a chain."""
    if chain not in HARDWARE_DB:
        return []
    if algo not in HARDWARE_DB[chain]:
        return []
    if device_type not in HARDWARE_DB[chain][algo]:
        return []
    
    results = []
    for device in HARDWARE_DB[chain][algo][device_type]:
        daily_electricity = (device['power'] / 1000) * 24 * electricity
        results.append({
            **device,
            'daily_electricity_usd': daily_electricity,
            'algorithm': algo,
            'chain': chain,
        })
    
    return results

def get_all_benchmarks():
    """Get all hardware benchmarks."""
    all_benchmarks = []
    
    for chain, algos in HARDWARE_DB.items():
        for algo, device_types in algos.items():
            for device_type, devices in device_types.items():
                for device in devices:
                    all_benchmarks.append({
                        'chain': chain,
                        'algorithm': algo,
                        'device_type': device_type,
                        **device,
                    })
    
    return all_benchmarks

def save_benchmarks():
    """Save benchmark registry."""
    benchmarks = get_all_benchmarks()
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_benchmarks': len(benchmarks),
        'chains': list(HARDWARE_DB.keys()),
        'benchmarks': benchmarks,
    }
    
    filepath = os.path.join(DATA_DIR, 'hardware_benchmarks.json')
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[SAVED] {filepath}")
    print(f"  Total benchmarks: {len(benchmarks)}")
    print(f"  Chains: {', '.join(HARDWARE_DB.keys())}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("Hardware Benchmark Registry")
    print(f"{'='*60}")
    
    for chain in HARDWARE_DB:
        print(f"\n[{chain}]")
        for algo in HARDWARE_DB[chain]:
            for device_type in HARDWARE_DB[chain][algo]:
                devices = HARDWARE_DB[chain][algo][device_type]
                print(f"  {algo} ({device_type}):")
                for d in devices[:3]:
                    print(f"    {d['name']}: {d['hashrate']:,.0f} H/s, {d['power']}W, ${d['cost']}")
    
    return output

if __name__ == '__main__':
    save_benchmarks()
