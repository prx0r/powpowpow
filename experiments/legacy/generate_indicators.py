"""
Advanced Technical Indicators for PowPowPow
L2 order book features + traditional indicators.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime

DATA_DIR = '/home/box/safetrade/tracked'
OUTPUT_DIR = os.path.join(BASE_DIR, 'chains')

def calculate_advanced_indicators(ohlcv_df, depth_df=None):
    """Calculate advanced technical indicators."""
    if ohlcv_df is None or len(ohlcv_df) < 30:
        return pd.DataFrame()
    
    df = ohlcv_df.copy()
    
    # === Price-Based ===
    df['return'] = df['close'].pct_change()
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['abs_return'] = df['return'].abs()
    
    # Volatility (multiple windows)
    for w in [5, 10, 20, 50]:
        df[f'volatility_{w}'] = df['return'].rolling(w).std()
        df[f'volatility_{w}_annualized'] = df[f'volatility_{w}'] * np.sqrt(365)
    
    # Moving Averages
    for w in [5, 10, 20, 50, 100]:
        df[f'sma_{w}'] = df['close'].rolling(w).mean()
        df[f'ema_{w}'] = df['close'].ewm(span=w).mean()
    
    # Momentum
    for w in [5, 10, 20]:
        df[f'momentum_{w}'] = df['close'] / df['close'].shift(w) - 1
        df[f'roc_{w}'] = (df['close'] - df['close'].shift(w)) / df['close'].shift(w) * 100
    
    # RSI (multiple periods)
    for w in [6, 14, 24]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(w).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(w).mean()
        rs = gain / loss
        df[f'rsi_{w}'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    df['macd_hist_pct'] = df['macd_hist'] / df['close'] * 100
    
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    for w in [7, 14, 21]:
        df[f'atr_{w}'] = tr.rolling(w).mean()
        df[f'atr_{w}_pct'] = df[f'atr_{w}'] / df['close'] * 100
    
    # Volume Features
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    df['obv'] = (np.sign(df['return']) * df['volume']).cumsum()
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    
    # Trend Strength
    df['adx'] = calculate_adx(df)
    df['cci'] = calculate_cci(df)
    df['mfi'] = calculate_mfi(df)
    
    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['stoch_k'] = (df['close'] - low_14) / (high_14 - low_14) * 100
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()
    
    # Williams %R
    df['williams_r'] = (high_14 - df['close']) / (high_14 - low_14) * -100
    
    # Price Patterns
    df['higher_high'] = df['high'] > df['high'].shift(1)
    df['lower_low'] = df['low'] < df['low'].shift(1)
    df['inside_bar'] = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    
    return df

def calculate_adx(df, period=14):
    """Calculate Average Directional Index."""
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx

def calculate_cci(df, period=20):
    """Calculate Commodity Channel Index."""
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma) / (0.015 * mad)
    return cci

def calculate_mfi(df, period=14):
    """Calculate Money Flow Index."""
    tp = (df['high'] + df['low'] + df['close']) / 3
    mf = tp * df['volume']
    
    pos_mf = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
    neg_mf = mf.where(tp < tp.shift(1), 0).rolling(period).sum()
    
    mfi = 100 - (100 / (1 + pos_mf / neg_mf))
    return mfi

def generate_features_for_coin(coin):
    """Generate all features for a single coin."""
    # Load OHLCV
    ohlcv_path = f'{DATA_DIR}/{coin}_1d_ohlcv.csv'
    if not os.path.exists(ohlcv_path):
        print(f"  No OHLCV for {coin}")
        return None
    
    ohlcv = pd.read_csv(ohlcv_path)
    ohlcv['date'] = pd.to_datetime(ohlcv['timestamp'], unit='ms')
    
    # Load depth
    depth_files = [f for f in os.listdir(DATA_DIR) if f.startswith(f'{coin}_depth') and f.endswith('.json')]
    depth_df = None
    if depth_files:
        with open(os.path.join(DATA_DIR, sorted(depth_files)[-1])) as f:
            depth_data = json.load(f)
        if depth_data:
            depth_df = pd.DataFrame(depth_data)
    
    # Calculate indicators
    features = calculate_advanced_indicators(ohlcv, depth_df)
    
    if len(features) > 0:
        # Save
        output_file = os.path.join(OUTPUT_DIR, coin, 'technical_indicators.csv')
        features.to_csv(output_file, index=False)
        print(f"  Generated {len(features.columns)} indicators for {len(features)} rows")
        return features
    
    return None

def generate_all():
    """Generate technical indicators for all coins."""
    print(f"\n{'='*60}")
    print(f"Generating Advanced Technical Indicators — {datetime.now()}")
    print(f"{'='*60}")
    
    coins = ['QUBIC', 'PRL', 'NOCK', 'XMR', 'XEL', 'XTM']
    results = {}
    
    for coin in coins:
        print(f"\n[{coin}]")
        try:
            features = generate_features_for_coin(coin)
            if features is not None:
                results[coin] = {
                    'rows': len(features),
                    'columns': len(features.columns),
                    'indicators': list(features.columns),
                }
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save summary
    summary_file = os.path.join(OUTPUT_DIR, 'indicators_summary.json')
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[SAVED] {summary_file}")
    
    return results

if __name__ == '__main__':
    generate_all()
