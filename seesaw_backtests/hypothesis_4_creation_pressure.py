"""
Hypothesis 4: Creation/Realization Pressure

Creation pressure:
  CP_t = EmissionUSD_t / BidDepth_{5%,t}

Realization pressure (future, needs miner flow data):
  RP_t = MinerExchangeFlowUSD_t / BidDepth_{5%,t}

Test whether high creation pressure (emissions overwhelming bid depth)
predicts future price weakness or liquidity response.

Currently proxies with volume/depth ratio.
"""

import numpy as np
import pandas as pd
from .base import SeesawTest


class CreationPressureTest(SeesawTest):
    name = 'h4_creation_pressure'
    description = 'Creation/realization pressure predicts price and liquidity response'

    signal_columns = [
        'creation_pressure_proxy',  # emission/depth proxy
        'turnover_ratio',          # volume relative to price level
        'return_conditioned_volume',  # volume conditioned on return direction
    ]

    def compute_signal(self, df, coin):
        df = df.copy()

        if 'close' not in df.columns or 'volume' not in df.columns:
            return df

        # Creation pressure proxy: volume / close (turnover relative to price)
        # In reality this would be EmissionUSD / BidDepth_5pct
        df['creation_pressure_proxy'] = df['volume'] / df['close'].replace(0, np.nan)

        # Turnover ratio: volume / 20-day MA volume
        vol_ma = df['volume'].rolling(20).mean()
        df['turnover_ratio'] = df['volume'] / vol_ma.replace(0, np.nan)

        # Return-conditioned volume: volume on up days vs down days
        returns = df['close'].pct_change()
        up_volume = df['volume'].where(returns > 0, 0)
        down_volume = df['volume'].where(returns < 0, 0)

        up_vol_ma = up_volume.rolling(20).mean()
        down_vol_ma = down_volume.rolling(20).mean()

        # Ratio of selling pressure to buying pressure
        df['return_conditioned_volume'] = down_vol_ma / up_vol_ma.replace(0, np.nan)

        return df


# Legacy alias
CreationPressure = CreationPressureTest
