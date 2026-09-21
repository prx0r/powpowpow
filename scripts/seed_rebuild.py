"""
Seed rebuild — one month at a time, compact+drop between months.

For each month-01: download free Tardis CSVs (drip targets) → load to
JSONL → build STATE + signals → compact to Parquet → drop month JSONL
→ delete .gz. Disk never holds more than one month of JSONL, so the
box can't fill even at full seed volume.

Usage:
    python3 scripts/seed_rebuild.py --months 2026/06/01,2026/07/01
    python3 scripts/seed_rebuild.py   # all four seed months
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

TARDIS_DIR = os.path.join(BASE_DIR, 'warehouse', 'tardis')

from tardis_drip import TARGETS, DTYPES  # noqa: E402

MONTHS = ['2026/06/01', '2026/07/01', '2026/08/01', '2026/09/01']
VENV_PY = '/home/ubuntu/.venvs/powpowpow/bin/python'


def _row_date(line):
    try:
        r = json.loads(line)
    except ValueError:
        return ''
    for k in ('date', 'exchange_time', 'event_time', 'receive_time'):
        v = r.get(k)
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return ''


def run(*args):
    r = subprocess.run([VENV_PY, *args], cwd=BASE_DIR,
                       capture_output=True, text=True)
    print(r.stdout[-1500:] if r.stdout else '')
    if r.returncode != 0:
        print(f"STEP FAILED: {' '.join(args)}\n{r.stderr[-800:]}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', default=','.join(MONTHS))
    args = ap.parse_args()
    for month in args.months.split(','):
        datestr = month.replace('/', '-')
        print(f"===== {month} =====", flush=True)
        # purge prior partial STATE/signals for this date (rebuild is clean)
        for table, key in (('daily_state', None), ('derived_signal', None)):
            for f in glob.glob(os.path.join(
                    BASE_DIR, 'warehouse', 'normalized', table,
                    'chain=*', 'date=*', 'hour=*.jsonl')):
                with open(f) as fh:
                    lines = fh.readlines()
                kept = [l for l in lines
                        if _row_date(l) != datestr]
                if len(kept) != len(lines):
                    with open(f, 'w') as fh:
                        fh.writelines(kept)
        for ex, sym in TARGETS:
            for dtype in DTYPES:
                fn = f"{ex}_{sym}_{dtype}_{month.replace('/', '')}.csv.gz"
                fp = os.path.join(TARDIS_DIR, fn)
                if os.path.exists(fp):
                    continue
                url = (f'https://datasets.tardis.dev/v1/{ex}/{dtype}/'
                       f'{month}/{sym}.csv.gz')
                try:
                    req = urllib.request.Request(
                        url, headers={'User-Agent': 'PowPowPow/1.0'})
                    data = urllib.request.urlopen(req, timeout=60).read()
                    open(fp, 'wb').write(data)
                    print(f"  got {fn} {len(data)/1e6:.1f}MB", flush=True)
                except Exception as e:
                    print(f"  miss {fn} ({str(e)[:60]})", flush=True)
        if run(os.path.join('scripts', 'load_tardis.py')) != 0:
            print(f"  LOAD FAILED {month}, continuing next month")
            continue
        run(os.path.join('scripts', 'dedupe_seed.py'), '--dates', datestr)
        run(os.path.join('scripts', 'build_daily_state.py'), '--date', datestr)
        run('signals.py', '--date', datestr)
        run(os.path.join('scripts', 'compact_stream.py'), '--date', datestr)
        # drop month JSONL + .gz (parquet + STATE now hold it)
        for table in ('orderbook_snapshot', 'trade', 'ticker'):
            d = os.path.join(BASE_DIR, 'warehouse', 'normalized', table,
                             'chain=venue', f'date={datestr}')
            shutil.rmtree(d, ignore_errors=True)
        for fn in os.listdir(TARDIS_DIR):
            if month.replace('/', '') in fn and fn.endswith('.csv.gz'):
                os.remove(os.path.join(TARDIS_DIR, fn))
        print(f"  [{month}] dropped JSONL+.gz", flush=True)
    run('factors.py', '--date', '2026-09-19')
    run('backtest.py')
    print("[REBUILD] done")


if __name__ == '__main__':
    main()
