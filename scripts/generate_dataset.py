"""
Training Dataset Generator for PowPowPow
Combines all data sources into ML-ready datasets.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime

CHAINS_DIR = '/home/box/powpowpow/chains'
DATA_DIR = '/home/box/safetrade/tracked'

def load_coin_data(coin):
    """Load all data for a coin."""
    result = {}
    
    # OHLCV
    ohlcv_path = f'{DATA_DIR}/{coin}_1d_ohlcv.csv'
    if os.path.exists(ohlcv_path):
        result['ohlcv'] = pd.read_csv(ohlcv_path)
    
    # Technical indicators
    indicators_path = f'{CHAINS_DIR}/{coin}/technical_indicators.csv'
    if os.path.exists(indicators_path):
        result['indicators'] = pd.read_csv(indicators_path)
    
    # Depth snapshots
    depth_files = [f for f in os.listdir(DATA_DIR) if f.startswith(f'{coin}_depth') and f.endswith('.json')]
    if depth_files:
        all_depth = []
        for f in sorted(depth_files):
            with open(os.path.join(DATA_DIR, f)) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    all_depth.extend(data)
        if all_depth:
            result['depth'] = all_depth
    
    # GitHub stats
    github_path = f'{CHAINS_DIR}/github_stats.json'
    if os.path.exists(github_path):
        with open(github_path) as f:
            all_github = json.load(f)
            if coin in all_github:
                result['github'] = all_github[coin]
    
    return result

def create_features(data, coin):
    """Create ML features from all data sources.
    
    IMPORTANT: L2 and GitHub features are NOT included in historical datasets
    because they are point-in-time snapshots, not historical time series.
    Pasting today's values onto historical rows creates lookahead bias.
    
    These features should only be used going forward as genuine point-in-time
    observations accumulate in the warehouse.
    """
    if 'indicators' not in data:
        return None
    
    df = data['indicators'].copy()
    
    # L2 and GitHub features intentionally excluded from historical datasets.
    # See 08_missing_data_layers_research.md and the data integrity diagnostic.
    # TODO: Once warehouse has genuine point-in-time L2/GitHub history,
    # join them by timestamp instead of broadcasting today's snapshot.
    
    # Create target: next day return
    if 'close' in df.columns:
        df['target_return'] = df['close'].shift(-1) / df['close'] - 1
        df['target_direction'] = (df['target_return'] > 0).astype(int)
    
    # Drop rows with NaN
    df = df.dropna(subset=['target_direction'])
    
    return df

def generate_dataset(coin):
    """Generate ML dataset for a single coin."""
    print(f"\n[{coin}]")
    
    data = load_coin_data(coin)
    if not data:
        print("  No data available")
        return None
    
    features = create_features(data, coin)
    if features is None or len(features) == 0:
        print("  Could not create features")
        return None
    
    # Save dataset
    output_file = f'{CHAINS_DIR}/{coin}/ml_dataset.csv'
    features.to_csv(output_file, index=False)
    
    print(f"  Samples: {len(features)}")
    print(f"  Features: {len(features.columns)}")
    print(f"  Target balance: {features['target_direction'].mean():.2%} up")
    
    return {
        'coin': coin,
        'samples': len(features),
        'features': len(features.columns),
        'target_balance': float(features['target_direction'].mean()),
    }

def generate_all():
    """Generate datasets for all coins."""
    print(f"\n{'='*60}")
    print(f"Generating ML Datasets — {datetime.now()}")
    print(f"{'='*60}")
    
    coins = ['QUBIC', 'PRL', 'NOCK', 'XEL', 'XTM']
    results = []
    
    for coin in coins:
        try:
            result = generate_dataset(coin)
            if result:
                results.append(result)
        except Exception as e:
            print(f"  Error: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("DATASET SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"  {r['coin']:8} | {r['samples']:4} samples | {r['features']:2} features | {r['target_balance']:.1%} up")
    
    # Save summary
    summary_file = f'{CHAINS_DIR}/datasets_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == '__main__':
    generate_all()
