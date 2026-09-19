"""
Base framework for Seesaw canonical backtests.

Each experiment:
1. Loads data from chains/ directory
2. Computes the relevant signal
3. Runs walk-forward correlation diagnostic
4. Reports sign stability across time splits
5. Compares against boring baselines

Walk-forward validation only. No random splits. No lookahead.
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple

CHAINS_DIR = '/home/box/powpowpow/chains'
BACKTESTS_DIR = os.path.join(CHAINS_DIR, 'backtests')


class SeesawExperiment:
    """Base class for canonical Seesaw experiments."""

    name: str = 'base'
    description: str = ''
    stage: int = 0  # 0=baselines, 1-4=reconstructable, 5-11=forward-only

    def __init__(self, coins: List[str] = None):
        self.coins = coins or ['PRL', 'QUBIC', 'NOCK', 'XEL', 'XTM']
        self.results = {}

    def load_daily(self, coin: str) -> Optional[pd.DataFrame]:
        """Load daily OHLCV + indicators for a coin."""
        path = os.path.join(CHAINS_DIR, coin, 'technical_indicators.csv')
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        return df

    def load_ml_dataset(self, coin: str) -> Optional[pd.DataFrame]:
        """Load the clean ML dataset (no L2/GitHub contamination)."""
        path = os.path.join(CHAINS_DIR, coin, 'ml_dataset.csv')
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        return df

    def compute_signal(self, df: pd.DataFrame, coin: str) -> pd.DataFrame:
        """Override: compute the hypothesis-specific signal columns."""
        raise NotImplementedError

    def walk_forward(self, df: pd.DataFrame, signal_col: str,
                     target_col: str, min_train: int = 60,
                     step: int = 20) -> Dict:
        """
        Walk-forward validation: train on expanding window, test next period.

        train: Jan–Mar → test: Apr
        train: Jan–Apr → test: May
        train: Jan–May → test: Jun
        ...
        """
        n = len(df)
        if n < min_train + step:
            return {'error': f'insufficient data ({n} rows)'}

        fold_results = []
        for train_end in range(min_train, n - step, step):
            train = df.iloc[:train_end]
            test = df.iloc[train_end:train_end + step]

            valid_train = train[[signal_col, target_col]].dropna()
            valid_test = test[[signal_col, target_col]].dropna()

            if len(valid_train) < 10 or len(valid_test) < 5:
                continue

            train_corr = valid_train[signal_col].corr(valid_train[target_col])
            test_corr = valid_test[signal_col].corr(valid_test[target_col])

            fold_results.append({
                'train_end_idx': train_end,
                'train_n': len(valid_train),
                'test_n': len(valid_test),
                'train_corr': round(train_corr, 4) if not np.isnan(train_corr) else None,
                'test_corr': round(test_corr, 4) if not np.isnan(test_corr) else None,
                'sign_stable': (
                    np.sign(train_corr) == np.sign(test_corr)
                    if not (np.isnan(train_corr) or np.isnan(test_corr))
                    else False
                ),
            })

        if not fold_results:
            return {'error': 'no valid folds'}

        # Aggregate
        test_corrs = [f['test_corr'] for f in fold_results if f['test_corr'] is not None]
        signs_stable = sum(1 for f in fold_results if f['sign_stable'])

        return {
            'n_folds': len(fold_results),
            'mean_test_corr': round(np.mean(test_corr := [f['test_corr'] for f in fold_results if f['test_corr'] is not None]), 4) if fold_results else None,
            'std_test_corr': round(np.std([f['test_corr'] for f in fold_results if f['test_corr'] is not None]), 4) if fold_results else None,
            'sign_stability_pct': round(signs_stable / len(fold_results) * 100, 1) if fold_results else 0,
            'folds': fold_results,
        }

        return result

    def corr_diagnostic(self, signal_col: str, target_col: str,
                        train: pd.DataFrame, test: pd.DataFrame) -> Dict:
        """Compute Pearson correlation of signal→target in train and test."""
        results = {}

        for name, subset in [('train', train), ('test', test)]:
            valid = subset[[signal_col, target_col]].dropna()
            if len(valid) < 10:
                results[name] = {'corr': np.nan, 'n': len(valid), 'p_value': np.nan}
                continue

            corr = valid[signal_col].corr(valid[target_col])
            n = len(valid)
            if abs(corr) < 1:
                t_stat = corr * np.sqrt((n - 2) / (1 - corr**2))
                from scipy import stats
                p = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 2))
            else:
                p = 0.0

            results[name] = {
                'corr': round(corr, 4),
                'n': n,
                'p_value': round(p, 4),
                'significant': p < 0.05,
            }

        if not np.isnan(results.get('train', {}).get('corr', np.nan)) and \
           not np.isnan(results.get('test', {}).get('corr', np.nan)):
            results['sign_stable'] = (
                np.sign(results['train']['corr']) == np.sign(results['test']['corr'])
            )
        else:
            results['sign_stable'] = False

        return results

    def run(self) -> Dict:
        """Run the experiment across all coins."""
        print(f"\n{'='*60}")
        print(f"EXPERIMENT {self.stage}: {self.name}")
        print(f"{self.description}")
        print(f"{'='*60}")

        all_results = {}

        for coin in self.coins:
            df = self.load_ml_dataset(coin)
            if df is None or len(df) < 50:
                print(f"  {coin}: insufficient data ({len(df) if df is not None else 0} rows)")
                continue

            try:
                df = self.compute_signal(df, coin)
                train, test = self.split_train_test(df)

                coin_results = {}
                for signal_col in self.signal_columns:
                    if signal_col not in df.columns:
                        continue
                    diag = self.corr_diagnostic(signal_col, 'target_return', train, test)
                    coin_results[signal_col] = diag

                    direction = 'stable' if diag['sign_stable'] else 'UNSTABLE'
                    train_r = diag['train']['corr']
                    test_r = diag['test']['corr']
                    sig = '***' if diag['test'].get('significant') else ''
                    print(f"  {coin:8} {signal_col:35} train={train_r:+.3f}  test={test_r:+.3f}  [{direction}] {sig}")

                all_results[coin] = coin_results

            except Exception as e:
                print(f"  {coin}: ERROR {e}")

        self.results = all_results
        return all_results

    def split_train_test(self, df, train_pct=0.6):
        n = len(df)
        split = int(n * train_pct)
        return df.iloc[:split].copy(), df.iloc[split:].copy()

    def summary(self) -> str:
        lines = [f"\n{'='*60}", f"SUMMARY: Experiment {self.stage} — {self.name}", f"{'='*60}"]
        for coin, signals in self.results.items():
            stable = [s for s, d in signals.items() if d.get('sign_stable')]
            sig = [s for s, d in signals.items() if d.get('test', {}).get('significant')]
            lines.append(f"  {coin}: {len(stable)} stable, {len(sig)} significant")
        return '\n'.join(lines)

    def save(self, output_dir: str = None):
        if output_dir is None:
            output_dir = BACKTESTS_DIR
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f'{self.name}.json')
        with open(path, 'w') as f:
            json.dump({
                'experiment': self.name,
                'stage': self.stage,
                'description': self.description,
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
            }, f, indent=2, default=str)
        print(f"\n  Saved: {path}")
