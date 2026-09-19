"""
Experiment J — Absorption

Absorption = (AggressiveBuy + BidAdds - BidCancels) / (AggressiveSell + MinerFlow)

Sustained Absorption < 1 predicts price weakness.
Test at multiple horizons.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class AbsorptionTest(SeesawExperiment):
    name = 'exp_j_absorption'
    description = 'Market absorption ratio predicts price weakness'
    stage = 7

    signal_columns = [
        'absorption_ratio',
        'sustained_absorption',
        'liquidity_stress',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Absorption ratio: buying pressure / total pressure
        up_volume = df['volume'].where(returns > 0, 0)
        down_volume = df['volume'].where(returns < 0, 0)

        rolling_up = up_volume.rolling(5).sum()
        rolling_down = down_volume.rolling(5).sum()

        df['absorption_ratio'] = rolling_up / (rolling_up + rolling_down).replace(0, np.nan)

        # Sustained absorption: 10-day rolling mean
        df['sustained_absorption'] = df['absorption_ratio'].rolling(10).mean()

        # Liquidity stress: high volume + wide spread proxy
        vol_ma = df['volume'].rolling(20).mean()
        vol_surge = df['volume'] / vol_ma.replace(0, np.nan)

        # Price impact: large moves with high volume = stress
        df['liquidity_stress'] = returns.abs() * vol_surge

        return df
