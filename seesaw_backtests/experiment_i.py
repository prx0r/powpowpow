"""
Experiment I — Miner Realization

RealizationRatio = MinerOriginatedExchangeFlow / Emission

Do miners hoard during rallies or dump immediately?
Currently proxies with volume asymmetry on up/down days.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class MinerRealizationTest(SeesawExperiment):
    name = 'exp_i_miner_realization'
    description = 'Miner selling behavior: hoard vs dump patterns'
    stage = 6

    signal_columns = [
        'realization_ratio_proxy',
        'hold_sell_signal',
        'flow_direction',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Realization ratio proxy: down-day volume / up-day volume
        # High = more selling pressure (miners realizing)
        up_volume = df['volume'].where(returns > 0, 0)
        down_volume = df['volume'].where(returns < 0, 0)

        rolling_up = up_volume.rolling(10).sum()
        rolling_down = down_volume.rolling(10).sum()

        df['realization_ratio_proxy'] = rolling_down / rolling_up.replace(0, np.nan)

        # Hold/sell signal: inverse of realization ratio
        # High = miners holding (up volume dominant)
        df['hold_sell_signal'] = 1.0 / df['realization_ratio_proxy'].replace(0, np.nan)

        # Flow direction: positive = net buying, negative = net selling
        df['flow_direction'] = np.sign(returns) * df['volume']

        return df
