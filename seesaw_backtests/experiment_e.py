"""
Experiment E — Price → Hashrate Causal Latency

L_{P→H} = argmax_k Corr(Return_t, Delta Hashrate_{t+k})

Tests at multiple lag windows to find the peak correlation.
"""

import numpy as np
import pandas as pd
from .base import SeesawExperiment


class CausalLatencyTest(SeesawExperiment):
    name = 'exp_e_causal_latency'
    description = 'Causal latency between price returns and supply response'
    stage = 4

    signal_columns = [
        'return_1d',
        'return_5d',
        'return_20d',
    ]

    def compute_signal(self, df, coin):
        df = df.copy()
        if 'close' not in df.columns:
            return df

        # Multi-horizon returns
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_20d'] = df['close'].pct_change(20)

        return df
