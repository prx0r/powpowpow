"""
Experiment C — Response Half-Life

After profitability shock (W_t > 2*sigma), measure cumulative capacity
response R(k) and find T_50 (time to half eventual response).

Compare: PRL GPUs vs XMR CPUs vs KAS ASICs.

Currently measures return-based response since we don't have
genuine hashrate time series yet.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class ResponseHalfLifeTest(SeesawExperiment):
    name = 'exp_c_response_half_life'
    description = 'Response half-life after profitability shock'
    stage = 2

    signal_columns = [
        'profitability_shock',
        'subsequent_return_5d',
        'subsequent_return_10d',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()
        rolling_ret = returns.rolling(10).mean()
        rolling_vol = returns.rolling(20).std()
        sharpe = rolling_ret / rolling_vol.replace(0, np.nan)

        # Profitability shock: where rolling Sharpe exceeds 2-sigma
        sharpe_mean = sharpe.rolling(60).mean()
        sharpe_std = sharpe.rolling(60).std()
        df['profitability_shock'] = (sharpe - sharpe_mean) / sharpe_std.replace(0, np.nan)

        # Subsequent returns (the response we're measuring)
        df['subsequent_return_5d'] = df['close'].pct_change(5).shift(-5)
        df['subsequent_return_10d'] = df['close'].pct_change(10).shift(-10)

        return df
