"""
Experiment K — Required Buy Pressure

Fit: r_{t+h} = b0 + b1*OFI_t + b2*MinerFlow_t + b3*Emission_t
        + b4*Depth_t + b5*Spread_t + b6*Vol_t + e

Solve for marginal buy-flow where E[r_{t+h}] = 0.
Gives empirical "required absorption to hold price flat."
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class RequiredBuyPressureTest(SeesawExperiment):
    name = 'exp_k_required_buy_pressure'
    description = 'Empirical buy pressure required to maintain price equilibrium'
    stage = 8

    signal_columns = [
        'ofi_proxy',
        'supply_pressure',
        'demand_pressure',
        'net_pressure',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        returns = df['close'].pct_change()
        vol_ma = df['volume'].rolling(20).mean()

        # OFI proxy: signed volume imbalance
        df['ofi_proxy'] = (returns * df['volume']).rolling(5).sum() / vol_ma.replace(0, np.nan)

        # Supply pressure: emission proxy + selling volume
        down_volume = df['volume'].where(returns < 0, 0)
        df['supply_pressure'] = down_volume.rolling(5).sum() / vol_ma.replace(0, np.nan)

        # Demand pressure: buying volume
        up_volume = df['volume'].where(returns > 0, 0)
        df['demand_pressure'] = up_volume.rolling(5).sum() / vol_ma.replace(0, np.nan)

        # Net pressure
        df['net_pressure'] = df['demand_pressure'] - df['supply_pressure']

        return df
