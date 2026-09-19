"""
Experiment D — Scarcity Persistence

SP = integral of max(W_t, 0) dt

How long until competition eliminates the resource premium?
Measures duration of above-trend profitability periods.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class ScarcityPersistenceTest(SeesawExperiment):
    name = 'exp_d_scarcity_persistence'
    description = 'Duration and magnitude of resource premium periods'
    stage = 3

    signal_columns = [
        'premium_duration',
        'premium_cumulative',
        'premium_decay_rate',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()
        rolling_ret = returns.rolling(10).mean()

        # Premium proxy: above-average returns
        mean_ret = rolling_ret.rolling(60).mean()
        premium = rolling_ret - mean_ret

        # Premium duration: rolling count of consecutive positive premium days
        is_premium = (premium > 0).astype(int)
        df['premium_duration'] = is_premium.rolling(20).sum()

        # Cumulative premium magnitude
        df['premium_cumulative'] = premium.rolling(20).apply(
            lambda x: x[x > 0].sum() if (x > 0).any() else 0, raw=True
        )

        # Decay rate: how quickly premium fades after peak
        peak = premium.rolling(20).max()
        current = premium
        df['premium_decay_rate'] = current / peak.replace(0, np.nan)

        return df
