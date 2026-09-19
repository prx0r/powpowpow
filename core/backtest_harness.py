"""
PowPowPow Core — Backtest Harness

Walk-forward validation only. No random splits. No lookahead.

Every feature must satisfy: observed_at <= prediction_time
not merely: event_time <= prediction_time
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Tuple

BACKTESTS_DIR = '/home/box/powpowpow/core/backtests'


def _ensure_dir():
    os.makedirs(BACKTESTS_DIR, exist_ok=True)


class BacktestHarness:
    """Canonical backtest framework for Seesaw experiments."""

    def __init__(self, name: str, description: str = ''):
        self.name = name
        self.description = description
        self.results = {}
        _ensure_dir()

    def walk_forward(
        self,
        df: pd.DataFrame,
        signal_col: str,
        target_col: str,
        min_train: int = 60,
        step: int = 20,
    ) -> Dict:
        """
        Walk-forward validation: train on expanding window, test next period.

        train: Jan–Mar → test: Apr
        train: Jan–Apr → test: May
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

        test_corrs = [f['test_corr'] for f in fold_results if f['test_corr'] is not None]
        signs_stable = sum(1 for f in fold_results if f['sign_stable'])

        return {
            'n_folds': len(fold_results),
            'mean_test_corr': round(np.mean(test_corrs), 4) if test_corrs else None,
            'std_test_corr': round(np.std(test_corrs), 4) if test_corrs else None,
            'sign_stability_pct': round(signs_stable / len(fold_results) * 100, 1),
            'folds': fold_results,
        }

    def purged_walk_forward(
        self,
        df: pd.DataFrame,
        signal_col: str,
        target_col: str,
        purge_days: int = 1,
        min_train: int = 60,
        step: int = 20,
    ) -> Dict:
        """
        Purged walk-forward: add purge gap around split to prevent leakage.
        """
        n = len(df)
        if n < min_train + step + purge_days:
            return {'error': 'insufficient data'}

        fold_results = []
        for train_end in range(min_train, n - step - purge_days, step):
            train = df.iloc[:train_end]
            # Purge: skip purge_days after train_end
            test_start = train_end + purge_days
            test = df.iloc[test_start:test_start + step]

            valid_train = train[[signal_col, target_col]].dropna()
            valid_test = test[[signal_col, target_col]].dropna()

            if len(valid_train) < 10 or len(valid_test) < 5:
                continue

            train_corr = valid_train[signal_col].corr(valid_train[target_col])
            test_corr = valid_test[signal_col].corr(valid_test[target_col])

            fold_results.append({
                'train_end_idx': train_end,
                'test_start_idx': test_start,
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

        test_corrs = [f['test_corr'] for f in fold_results if f['test_corr'] is not None]
        signs_stable = sum(1 for f in fold_results if f['sign_stable'])

        return {
            'n_folds': len(fold_results),
            'purge_days': purge_days,
            'mean_test_corr': round(np.mean(test_corrs), 4) if test_corrs else None,
            'std_test_corr': round(np.std(test_corrs), 4) if test_corrs else None,
            'sign_stability_pct': round(signs_stable / len(fold_results) * 100, 1),
            'folds': fold_results,
        }

    def event_study(
        self,
        df: pd.DataFrame,
        event_mask: pd.Series,
        target_col: str,
        window_before: int = 7,
        window_after: int = 30,
    ) -> Dict:
        """
        Event study: show average returns from t-window_before through t+window_after.
        """
        event_indices = df.index[event_mask].tolist()
        if not event_indices:
            return {'error': 'no events found'}

        car_paths = []
        for idx in event_indices:
            start = max(0, idx - window_before)
            end = min(len(df), idx + window_after + 1)
            window = df.iloc[start:end]

            if target_col in window.columns:
                returns = window[target_col].fillna(0).values
                # Cumulative abnormal return
                car = np.cumsum(returns)
                # Align to event center
                offset = idx - start
                car_centered = car - car[offset]  # normalize to 0 at event
                car_paths.append(car_centered)

        if not car_paths:
            return {'error': 'no valid event windows'}

        # Average across events
        max_len = max(len(p) for p in car_paths)
        padded = np.full((len(car_paths), max_len), np.nan)
        for i, p in enumerate(car_paths):
            padded[i, :len(p)] = p

        mean_car = np.nanmean(padded, axis=0)
        std_car = np.nanstd(padded, axis=0)

        return {
            'n_events': len(event_indices),
            'window_before': window_before,
            'window_after': window_after,
            'mean_car': mean_car.tolist(),
            'std_car': std_car.tolist(),
            'car_at_peak': float(np.nanmax(mean_car)),
            'car_at_trough': float(np.nanmin(mean_car)),
        }

    def save(self, results: Dict = None):
        """Save backtest results."""
        if results is None:
            results = self.results

        filepath = os.path.join(BACKTESTS_DIR, f'{self.name}.json')
        with open(filepath, 'w') as f:
            json.dump({
                'harness': self.name,
                'description': self.description,
                'timestamp': datetime.now().isoformat(),
                'results': results,
            }, f, indent=2, default=str)

        print(f"  Saved: {filepath}")
