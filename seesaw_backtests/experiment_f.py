"""
Experiment F — Profitability > Price as Supply Predictor

Compare:
  Delta H_{t+k} = f(Return_t)
vs:
  Delta H_{t+k} = f(MiningMargin_t)

If Seesaw is right, profitability explains supply better than price alone.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class ProfitabilityVsPriceTest(SeesawExperiment):
    name = 'exp_f_profitability_vs_price'
    description = 'Profitability explains supply response better than price alone'
    stage = 4

    signal_columns = [
        'price_signal_only',
        'profitability_signal_only',
        'profitability_minus_price',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()
        vol_ma = df['volume'].rolling(20).mean()
        vol_ratio = df['volume'] / vol_ma.replace(0, np.nan)

        # Price-only signal
        df['price_signal_only'] = returns.rolling(10).mean()

        # Profitability signal (volume-adjusted)
        df['profitability_signal_only'] = returns.rolling(10).mean() * vol_ratio

        # Differential: profitability minus price
        df['profitability_minus_price'] = (
            df['profitability_signal_only'] - df['price_signal_only']
        )

        return df
