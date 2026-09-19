"""
Experiment H — Creation Pressure

CreationPressure_t = (NewTokens_t * Price_t) / BidDepth_{5%,t}

Test whether high creation pressure predicts future return,
spread widening, volatility, bid depletion, OFI.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class CreationPressureTest(SeesawExperiment):
    name = 'exp_h_creation_pressure'
    description = 'Token creation pressure predicts price and liquidity response'
    stage = 5

    signal_columns = [
        'creation_pressure',
        'turnover_ratio',
        'selling_pressure',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Creation pressure proxy: volume / close (turnover relative to price)
        df['creation_pressure'] = df['volume'] / df['close'].replace(0, np.nan)

        # Turnover ratio: volume / 20-day MA volume
        vol_ma = df['volume'].rolling(20).mean()
        df['turnover_ratio'] = df['volume'] / vol_ma.replace(0, np.nan)

        # Selling pressure: down-day volume / total volume
        down_volume = df['volume'].where(returns < 0, 0)
        rolling_down = down_volume.rolling(10).sum()
        rolling_total = df['volume'].rolling(10).sum()
        df['selling_pressure'] = rolling_down / rolling_total.replace(0, np.nan)

        return df
