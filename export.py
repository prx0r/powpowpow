"""
Backtest Data Exporter
Creates clean datasets for backtesting.
"""

import json
import os
import csv
import sys
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CHAINS_DIR = os.path.join(BASE_DIR, 'chains')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

def load_json(filename):
    path = os.path.join(CHAINS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def export_ohlcv():
    """Export OHLCV data for all coins.

    Legacy SafeTrade tracked dir (old /home/box machine) is checked first
    via SAFETRADE_TRACKED_DIR env; otherwise exports daily mid_ohlc derived
    from our own warehouse daily_state table.
    """
    print("[EXPORT] OHLCV data...")

    safetrade_dir = os.environ.get('SAFETRADE_TRACKED_DIR', '')
    exported = []

    for coin in ['QUBIC', 'PRL', 'NOCK', 'XEL', 'XTM']:
        ohlcv_path = os.path.join(safetrade_dir, f'{coin}_1d_ohlcv.csv') if safetrade_dir else ''
        if ohlcv_path and os.path.exists(ohlcv_path):
            df = pd.read_csv(ohlcv_path)
            output_path = os.path.join(EXPORT_DIR, f'{coin}_ohlcv.csv')
            df.to_csv(output_path, index=False)
            exported.append(coin)
            print(f"  ✓ {coin}: {len(df)} rows (safetrade tracked)")
            continue
        # Fallback: our own daily_state mid OHLC across venues
        rows = []
        for chain in ('venue', 'safetrade'):
            table_dir = os.path.join(BASE_DIR, 'warehouse', 'normalized', 'daily_state', f'chain={chain}')
            if not os.path.isdir(table_dir):
                continue
            for date_dir in sorted(os.listdir(table_dir)):
                for hf in sorted(os.listdir(os.path.join(table_dir, date_dir))):
                    if not hf.endswith('.jsonl'):
                        continue
                    with open(os.path.join(table_dir, date_dir, hf)) as fh:
                        for line in fh:
                            try:
                                r = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if (r.get('symbol') or '').upper() == coin and r.get('mid_close'):
                                rows.append({'date': r.get('date'), 'venue': r.get('venue'),
                                             'open': r.get('mid_open'), 'high': r.get('mid_high'),
                                             'low': r.get('mid_low'), 'close': r.get('mid_close'),
                                             'volume': r.get('trade_notional_sum')})
        if rows:
            output_path = os.path.join(EXPORT_DIR, f'{coin}_ohlcv.csv')
            pd.DataFrame(rows).to_csv(output_path, index=False)
            exported.append(coin)
            print(f"  ✓ {coin}: {len(rows)} rows (warehouse daily_state)")
        else:
            print(f"  - {coin}: no source data (set SAFETRADE_TRACKED_DIR or run venue_l2)")

    return exported

def export_factors():
    """Export cross-chain factor table."""
    print("[EXPORT] Factor table...")
    
    factors_path = os.path.join(CHAINS_DIR, 'factors', 'cross_chain_factors.json')
    if os.path.exists(factors_path):
        with open(factors_path) as f:
            factors = json.load(f)
        
        # Convert to CSV
        rows = []
        for symbol, data in factors.items():
            row = {k: v for k, v in data.items() if not isinstance(v, (dict, list))}
            rows.append(row)
        
        if rows:
            output_path = os.path.join(EXPORT_DIR, 'cross_chain_factors.csv')
            pd.DataFrame(rows).to_csv(output_path, index=False)
            print(f"  ✓ {len(rows)} chains exported")
            return True
    return False

def export_economics():
    """Export miner economics."""
    print("[EXPORT] Miner economics...")
    
    econ_path = os.path.join(CHAINS_DIR, 'economics', 'miner_economics.json')
    if os.path.exists(econ_path):
        with open(econ_path) as f:
            economics = json.load(f)
        
        rows = []
        for symbol, data in economics.items():
            row = {
                'symbol': symbol,
                'daily_emission_usd': data.get('daily_emission_usd'),
                'daily_sell_pressure_usd': data.get('daily_sell_pressure_usd'),
                'absorption_ratio': data.get('absorption_ratio'),
                'dilution_pressure': data.get('dilution_pressure'),
            }
            rows.append(row)
        
        if rows:
            output_path = os.path.join(EXPORT_DIR, 'miner_economics.csv')
            pd.DataFrame(rows).to_csv(output_path, index=False)
            print(f"  ✓ {len(rows)} chains exported")
            return True
    return False

def export_backtest_dataset():
    """Create combined backtest dataset."""
    print("[EXPORT] Backtest dataset...")
    
    # Load all data
    factors_path = os.path.join(EXPORT_DIR, 'cross_chain_factors.csv')
    economics_path = os.path.join(EXPORT_DIR, 'miner_economics.csv')
    
    if os.path.exists(factors_path) and os.path.exists(economics_path):
        factors = pd.read_csv(factors_path)
        economics = pd.read_csv(economics_path)
        
        # Merge on symbol
        merged = factors.merge(economics, on='symbol', how='outer', suffixes=('_factor', '_econ'))
        
        output_path = os.path.join(EXPORT_DIR, 'backtest_dataset.csv')
        merged.to_csv(output_path, index=False)
        print(f"  ✓ {len(merged)} rows exported")
        return True
    return False

def export_all():
    """Run all exports."""
    print(f"\n{'='*60}")
    print(f"Exporting Backtest Data — {datetime.now()}")
    print(f"{'='*60}")
    
    export_ohlcv()
    export_factors()
    export_economics()
    export_backtest_dataset()
    
    # List exported files
    print(f"\n{'='*60}")
    print("Exported Files")
    print(f"{'='*60}")
    for f in sorted(os.listdir(EXPORT_DIR)):
        size = os.path.getsize(os.path.join(EXPORT_DIR, f))
        print(f"  {f:40} {size:>10,} bytes")

if __name__ == '__main__':
    export_all()
