"""
Hypothesis 2: Price → Profitability → Hashrate → Future Price

The full reflexive loop:

P_t ↑ → Margin_t ↑ → H_{t+k} ↑ → R_{t+m}?

Test whether large hashrate responses subsequently predict weaker returns.
This is the core Seesaw: does supply response eventually exhaust momentum?
"""

import numpy as np
import pandas as pd
from .base import SeesawTest


class ReflexiveLoopTest(SeesawTest):
    name = 'h2_reflexive_loop'
    description = 'Full reflexive loop: price → margin → hashrate response → exhaustion'

    signal_columns = [
        'exhaustion_signal',      # large move + abnormal turnover → lower next return
        'momentum_fade',          # rolling return vs subsequent return
        'volatility_regime',      # Bollinger width as regime indicator
    ]

    def compute_signal(self, df, coin):
        df = df.copy()

        if 'close' not in df.columns:
            return df

        returns = df['close'].pct_change()

        # Exhaustion signal: abs return * volume ratio → next-period return
        vol_ma = df['volume'].rolling(20).mean()
        vol_ratio = df['volume'] / vol_ma.replace(0, np.nan)

        df['exhaustion_signal'] = returns.abs() * vol_ratio

        # Momentum fade: 10-day return → subsequent 5-day return
        mom_10 = df['close'].pct_change(10)
        mom_5_fwd = df['close'].pct_change(5).shift(-5)
        df['momentum_fade'] = mom_10  # target will be next-period return

        # Volatility regime: Bollinger width
        if 'BB_upper' in df.columns and 'BB_lower' in df.columns and 'close' in df.columns:
            df['volatility_regime'] = (df['BB_upper'] - df['BB_lower']) / df['close']
        else:
            # Fallback: 20-day rolling std of returns
            df['volatility_regime'] = returns.rolling(20).std()

        return df


# Legacy alias
ReflexiveLoop = ReflexiveLoopTest
