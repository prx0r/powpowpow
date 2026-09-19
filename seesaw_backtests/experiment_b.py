"""
Experiment B — Resource Premium Predicts Supply (Canonical Seesaw)

Delta Capacity_{t+k} = alpha + beta * W_t + epsilon

Where W_t = ProtocolRevenuePerResourceHour - ExternalRevenuePerResourceHour
Test across 1h, 6h, 12h, 1d, 3d, 7d lags.

Currently proxies mining margin with volume-weighted price momentum.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class ResourcePremiumTest(SeesawExperiment):
    name = 'exp_b_resource_premium'
    description = 'Resource premium (wedge) predicts supply capacity response'
    stage = 1

    signal_columns = [
        'mining_wedge_proxy',
        'profitability_signal',
        'volume_weighted_return',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()
        vol_ma = df['volume'].rolling(20).mean()
        vol_ratio = df['volume'] / vol_ma.replace(0, np.nan)

        # Mining wedge proxy: volume-weighted return magnitude
        # Positive = mining is more profitable than alternatives
        df['mining_wedge_proxy'] = returns.rolling(5).mean() * vol_ratio

        # Profitability signal: rolling Sharpe-like ratio
        rolling_ret = returns.rolling(10).mean()
        rolling_vol = returns.rolling(20).std()
        df['profitability_signal'] = rolling_ret / rolling_vol.replace(0, np.nan)

        # Volume-weighted return
        df['volume_weighted_return'] = returns * vol_ratio

        return df
