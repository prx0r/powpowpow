"""
PowPowPow Core — BTC Baseline & Market Context

For every asset estimate:
  r_asset,t = alpha + beta_BTC * r_BTC,t + epsilon_t

Study residual:
  r_idio,t = r_asset,t - beta_BTC * r_BTC,t

If PRL rises 15% while BTC rises 12%, "PRL rose" is much less interesting
than if PRL rises 15% while BTC is flat.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Tuple

PANEL_DIR = '/home/box/powpowpow/core/panel'


def load_asset_series(asset: str, panel_type: str = '1d') -> Optional[pd.DataFrame]:
    """Load price/return series for an asset from the panel."""
    panel_dir = os.path.join(PANEL_DIR, f"seesaw_panel_{panel_type}")
    asset_dir = os.path.join(panel_dir, f"asset={asset}")
    if not os.path.exists(asset_dir):
        return None

    records = []
    for date_dir in sorted(os.listdir(asset_dir)):
        if not date_dir.startswith('date='):
            continue
        date_path = os.path.join(asset_dir, date_dir)
        for fname in sorted(os.listdir(date_path)):
            if fname.endswith('.jsonl'):
                with open(os.path.join(date_path, fname)) as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))

    if not records:
        return None

    df = pd.DataFrame(records)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def compute_btc_betas(asset_df: pd.DataFrame, btc_df: pd.DataFrame,
                      windows: list = [7, 30, 90]) -> pd.DataFrame:
    """
    Compute rolling BTC betas for an asset.

    Returns DataFrame with columns: btc_beta_7d, btc_beta_30d, btc_beta_90d,
    residual_return, residual_volatility.
    """
    if asset_df is None or btc_df is None:
        return pd.DataFrame()

    # Align on timestamp
    merged = pd.merge(
        asset_df[['timestamp', 'return_1d']].rename(columns={'return_1d': 'asset_return'}),
        btc_df[['timestamp', 'return_1d']].rename(columns={'return_1d': 'btc_return'}),
        on='timestamp', how='inner'
    )

    if len(merged) < 10:
        return pd.DataFrame()

    result = merged[['timestamp']].copy()
    result['asset_return'] = merged['asset_return']
    result['btc_return'] = merged['btc_return']

    for w in windows:
        beta_col = f'btc_beta_{w}d'
        result[beta_col] = merged['asset_return'].rolling(w).cov(
            merged['btc_return']
        ) / merged['btc_return'].rolling(w).var()

        # Residual return
        predicted = result[beta_col] * merged['btc_return']
        result['residual_return'] = merged['asset_return'] - predicted

    # Residual volatility (20d rolling)
    result['residual_volatility'] = result['residual_return'].rolling(20).std()

    # Residual return from 30d beta (default)
    if 'btc_beta_30d' in result.columns:
        predicted_30 = result['btc_beta_30d'] * merged['btc_return']
        result['residual_return'] = merged['asset_return'] - predicted_30

    return result


def compute_market_context(btc_df: pd.DataFrame = None,
                           eth_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Compute broad market context variables.
    """
    if btc_df is None:
        return pd.DataFrame()

    result = btc_df[['timestamp']].copy()
    result['btc_return'] = btc_df.get('return_1d', 0)
    result['btc_volatility'] = btc_df.get('return_1d', pd.Series()).rolling(20).std()

    if eth_df is not None:
        merged_eth = pd.merge(
            btc_df[['timestamp']],
            eth_df[['timestamp', 'return_1d']].rename(columns={'return_1d': 'eth_return'}),
            on='timestamp', how='left'
        )
        result['eth_return'] = merged_eth['eth_return']

    # Crypto market return (equal-weight proxy)
    result['crypto_market_return'] = result['btc_return']
    if 'eth_return' in result.columns:
        result['crypto_market_return'] = (
            result['btc_return'] * 0.6 + result['eth_return'].fillna(0) * 0.4
        )

    result['crypto_market_volatility'] = result['crypto_market_return'].rolling(20).std()

    return result


def compute_incremental_value_test(
    asset_returns: pd.Series,
    btc_returns: pd.Series,
    m1_features: pd.DataFrame = None,
    m2_features: pd.DataFrame = None,
    m3_features: pd.DataFrame = None,
    horizon: int = 1,
) -> Dict[str, float]:
    """
    Incremental value test: does each layer add predictive power?

    M0 = BTC + own price/volume
    M1 = M0 + profitability + wedge + hashrate
    M2 = M1 + depth + OFI + miner flow
    M3 = M2 + events

    Returns dict with R² for each model.
    """
    from sklearn.linear_model import LinearRegression

    results = {}
    y = asset_returns.shift(-horizon).dropna()

    # M0: BTC return only
    X0 = btc_returns.reindex(y.index).dropna()
    y0 = y.reindex(X0.index).dropna()
    X0 = X0.reindex(y0.index)

    if len(y0) > 20:
        reg0 = LinearRegression().fit(X0.values.reshape(-1, 1), y0.values)
        results['M0_r2'] = reg0.score(X0.values.reshape(-1, 1), y0.values)
    else:
        results['M0_r2'] = 0.0

    # M1: BTC + resource features
    if m1_features is not None:
        X1 = pd.concat([X0, m1_features.reindex(y0.index)], axis=1).dropna()
        y1 = y.reindex(X1.index).dropna()
        X1 = X1.reindex(y1.index)
        if len(y1) > 20 and X1.shape[1] > 1:
            reg1 = LinearRegression().fit(X1.values, y1.values)
            results['M1_r2'] = reg1.score(X1.values, y1.values)
        else:
            results['M1_r2'] = results['M0_r2']
    else:
        results['M1_r2'] = results['M0_r2']

    results['M1_delta'] = results['M1_r2'] - results['M0_r2']

    return results


if __name__ == '__main__':
    print("BTC baseline module ready.")
    print("Usage:")
    print("  1. Load BTC + asset returns from panel")
    print("  2. Compute rolling betas and residuals")
    print("  3. Run incremental value tests")
    print("  4. Content hook: 'PRL up 18%, but only 3% explained by BTC'")
