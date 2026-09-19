"""
Hypothesis 5: Absorption Failure

Measure:
  A_t = (AggressiveBuy + NetBidAdds) / (AggressiveSell + MinerFlow)

Sustained A < 1 predicts price weakness better than ordinary technicals.

Currently proxies with order flow imbalance and volume asymmetry.
"""

import numpy as np
import pandas as pd
from .base import SeesawTest


class AbsorptionFailureTest(SeesawTest):
    name = 'h5_absorption_failure'
    description = 'Absorption failure predicts sustained price weakness'

    signal_columns = [
        'absorption_ratio',       # buying vs selling pressure proxy
        'sustained_imbalance',    # multi-day absorption failure
        'volume_price_divergence',  # volume up + price down = distribution
    ]

    def compute_signal(self, df, coin):
        df = df.copy()

        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Absorption ratio proxy: volume on up days / total volume
        up_volume = df['volume'].where(returns > 0, 0)
        rolling_up = up_volume.rolling(5).sum()
        rolling_total = df['volume'].rolling(5).sum()

        df['absorption_ratio'] = rolling_up / rolling_total.replace(0, np.nan)

        # Sustained imbalance: rolling mean of absorption ratio
        # Values below 0.5 suggest sustained selling pressure
        df['sustained_imbalance'] = df['absorption_ratio'].rolling(10).mean()

        # Volume-price divergence: volume increasing while price decreasing
        vol_trend = df['volume'].rolling(10).mean() / df['volume'].rolling(30).mean()
        price_trend = df['close'].rolling(10).mean() / df['close'].rolling(30).mean()

        # Divergence = high volume growth + negative price growth
        df['volume_price_divergence'] = vol_trend / price_trend.replace(0, np.nan)

        return df


# Legacy alias
AbsorptionFailure = AbsorptionFailureTest
