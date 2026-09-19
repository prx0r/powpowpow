"""
Hypothesis 1: Profitability → Capacity

Delta Hashrate_{t+k} = f(MiningMargin_t)

Test lags from hours to days. Gives supply-response latency and elasticity.

Currently proxies mining margin with volume-weighted price momentum
since we don't yet have genuine hashrate/difficulty history.
"""

import numpy as np
import pandas as pd
from .base import SeesawTest


class ProfitabilityCapacityTest(SeesawTest):
    name = 'h1_profitability_capacity'
    description = 'Mining margin predicts subsequent hashrate/capacity response'

    signal_columns = [
        'mining_margin_proxy',    # volume-weighted return as margin proxy
        'abs_return',             # absolute return (magnitude of move)
        'volume_ratio',           # volume vs MA(20) as activity proxy
    ]

    def compute_signal(self, df, coin):
        # Mining margin proxy: volume-weighted absolute return
        # In a real implementation this would use actual mining revenue data
        df = df.copy()

        if 'close' in df.columns and 'volume' in df.columns:
            returns = df['close'].pct_change()
            abs_ret = returns.abs()

            # Volume ratio: current volume / 20-day MA
            vol_ma = df['volume'].rolling(20).mean()
            vol_ratio = df['volume'] / vol_ma.replace(0, np.nan)

            df['mining_margin_proxy'] = abs_ret * vol_ratio
            df['abs_return'] = abs_ret
            df['volume_ratio'] = vol_ratio

        return df


# Legacy alias
ProfitabilityCapacity = ProfitabilityCapacityTest
