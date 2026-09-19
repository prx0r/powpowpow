"""
Experiment G — Hashrate Overshoot → Future Return

HashrateOvershoot = H_t - H_hat_t

Test if too much hardware arrived relative to current economics
→ structural selling → poorer subsequent token returns.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class HashrateOvershootTest(SeesawExperiment):
    name = 'exp_g_hashrate_overshoot'
    description = 'Excess supply relative to economics predicts future returns'
    stage = 5

    signal_columns = [
        'supply_demand_imbalance',
        'return_reversion_signal',
        'volume_surge',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()
        vol_ma = df['volume'].rolling(20).mean()

        # Supply-demand imbalance: volume surge relative to price trend
        # High volume + falling price = supply overshoot
        vol_surge = df['volume'] / vol_ma.replace(0, np.nan)
        price_trend = df['close'].pct_change(10)

        df['supply_demand_imbalance'] = vol_surge * (-price_trend)

        # Return reversion: big moves tend to reverse
        df['return_reversion_signal'] = -returns.rolling(5).mean() * returns.rolling(5).std()

        # Volume surge indicator
        df['volume_surge'] = vol_surge

        return df
