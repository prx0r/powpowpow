"""
Seesaw Backtest Runner — 11 Canonical Experiments

Runs all experiments A-K and produces a combined report.
Every new dataset must improve these benchmark tests.

Usage:
    python3 -m seesaw_backtests.runner
    python3 -m seesaw_backtests.runner --coins PRL QUBIC
    python3 -m seesaw_backtests.runner --stage 0  # baselines only
"""

import json
import os
import sys
from datetime import datetime

from .experiment_a import PriceIncentiveTest
from .experiment_b import ResourcePremiumTest
from .experiment_c import ResponseHalfLifeTest
from .experiment_d import ScarcityPersistenceTest
from .experiment_e import CausalLatencyTest
from .experiment_f import ProfitabilityVsPriceTest
from .experiment_g import HashrateOvershootTest
from .experiment_h import CreationPressureTest
from .experiment_i import MinerRealizationTest
from .experiment_j import AbsorptionTest
from .experiment_k import RequiredBuyPressureTest

CHAINS_DIR = '/home/box/powpowpow/chains'
BACKTESTS_DIR = os.path.join(CHAINS_DIR, 'backtests')


def get_all_experiments(coins=None):
    """Return all 11 experiment instances."""
    return [
        PriceIncentiveTest(coins),
        ResourcePremiumTest(coins),
        ResponseHalfLifeTest(coins),
        ScarcityPersistenceTest(coins),
        CausalLatencyTest(coins),
        ProfitabilityVsPriceTest(coins),
        HashrateOvershootTest(coins),
        CreationPressureTest(coins),
        MinerRealizationTest(coins),
        AbsorptionTest(coins),
        RequiredBuyPressureTest(coins),
    ]


def run_all(coins=None, stage=None):
    """Run experiments and produce combined report."""
    experiments = get_all_experiments(coins)

    if stage is not None:
        experiments = [e for e in experiments if e.stage == stage]

    print(f"\n{'#'*60}")
    print(f"SEESAW CANONICAL BACKTESTS — {len(experiments)} experiments")
    print(f"Started: {datetime.now()}")
    print(f"Coins: {coins or ['PRL', 'QUBIC', 'NOCK', 'XEL', 'XTM']}")
    print(f"Stage filter: {'all' if stage is None else stage}")
    print(f"{'#'*60}")

    all_results = {}
    for exp in experiments:
        results = exp.run()
        all_results[exp.name] = {
            'stage': exp.stage,
            'description': exp.description,
            'results': results,
        }
        exp.save()
        print(exp.summary())

    # Combined report
    os.makedirs(BACKTESTS_DIR, exist_ok=True)
    report_path = os.path.join(BACKTESTS_DIR, 'combined_report.json')
    with open(report_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'n_experiments': len(experiments),
            'experiments': list(all_results.keys()),
            'results': all_results,
        }, f, indent=2, default=str)

    # Findings summary
    print(f"\n{'#'*60}")
    print("COMBINED FINDINGS")
    print(f"{'#'*60}")

    stable_signals = []
    for hypo_name, data in all_results.items():
        for coin, signals in data['results'].items():
            for sig_name, diag in signals.items():
                if isinstance(diag, dict) and diag.get('sign_stable') and diag.get('test', {}).get('significant'):
                    stable_signals.append({
                        'experiment': hypo_name,
                        'stage': data['stage'],
                        'coin': coin,
                        'signal': sig_name,
                        'train_corr': diag['train']['corr'],
                        'test_corr': diag['test']['corr'],
                    })

    if stable_signals:
        print(f"\n  Found {len(stable_signals)} stable+significant signals:")
        for s in stable_signals:
            print(f"    [{s['stage']}] {s['coin']:8} {s['signal']:35} train={s['train_corr']:+.3f} test={s['test_corr']:+.3f}")
    else:
        print("\n  No stable+significant signals found yet.")
        print("  Expected with current data (no L2/miner/resource history).")
        print("  Stages 0-4 use reconstructable data to develop methodology.")
        print("  Stages 5-11 require genuine forward-collected ephemeral data.")

    print(f"\n  Results saved to: {BACKTESTS_DIR}/")
    print(f"{'#'*60}\n")

    return all_results


if __name__ == '__main__':
    coins = None
    stage = None

    args = sys.argv[1:]
    if '--coins' in args:
        idx = args.index('--coins')
        coins = args[idx + 1:]
    if '--stage' in args:
        idx = args.index('--stage')
        stage = int(args[idx + 1])

    run_all(coins=coins, stage=stage)
