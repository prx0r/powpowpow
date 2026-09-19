"""
Experiment A — Price Creates Machine Incentive

Does token appreciation increase mining/resource profitability?

Delta Margin_t = f(Delta P_t)

Mostly a sanity test. Can run historically on reconstructable data.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class PriceIncentiveTest(SeesawExperiment):
    name = 'exp_a_price_incentive'
    description = 'Token appreciation increases mining/resource profitability'
    stage = 0

    signal_columns = [
        'price_momentum',
        'price_volatility',
        'volume_price_correlation',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # 5-day momentum
        df['price_momentum'] = df['close'].pct_change(5)

        # 20-day volatility
        df['price_volatility'] = returns.rolling(20).std()

        # Volume-price correlation (20-day rolling)
        df['volume_price_correlation'] = returns.rolling(20).corr(
            df['volume'].pct_change().rolling(20).mean()
        )

        return df
