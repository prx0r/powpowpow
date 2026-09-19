"""
Hypothesis 3: Resource Allocation Wedge

W_t = Profit_mine - Profit_rent

Then test: W_t → Delta Capacity_{t+k}

The purest Seesaw backtest. Currently proxies with:
- Mining proxy: volume-weighted price return (mining revenue signal)
- Rental proxy: external GPU market data when available

Without genuine rental/mine profitability data, we test the
observable component: does relative attractiveness predict capacity flow?
"""

import numpy as np
import pandas as pd
from .base import SeesawTest


class ResourceWedgeTest(SeesawTest):
    name = 'h3_resource_wedge'
    description = 'Resource allocation wedge predicts capacity migration'

    signal_columns = [
        'wedge_proxy',            # relative attractiveness signal
        'relative_volume',        # volume vs cross-coin median
        'spread_compression',     # spread narrowing as capacity inflow signal
    ]

    def compute_signal(self, df, coin):
        df = df.copy()

        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Wedge proxy: return magnitude * sign(streak)
        # Positive wedge = coin outperforming → should attract capacity
        rolling_ret = returns.rolling(5).mean()
        rolling_vol = returns.rolling(20).std()

        # Sharpe-like ratio as proxy for relative attractiveness
        df['wedge_proxy'] = rolling_ret / rolling_vol.replace(0, np.nan)

        # Relative volume: this coin's volume vs its own 20-day MA
        vol_ma = df['volume'].rolling(20).mean()
        df['relative_volume'] = df['volume'] / vol_ma.replace(0, np.nan)

        # Spread compression: if we have high/low data
        if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            spread = (df['high'] - df['low']) / df['close']
            spread_ma = spread.rolling(20).mean()
            df['spread_compression'] = spread / spread_ma.replace(0, np.nan)
        else:
            df['spread_compression'] = np.nan

        return df


# Legacy alias
ResourceWedge = ResourceWedgeTest
