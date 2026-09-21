"""
Tardis free-drip — every month-first becomes free; pull it forever.

For our symbol set, checks datasets.tardis.dev for month-01 CSVs
(trades + book_snapshot_25), downloads whatever is missing vs
warehouse/tardis/, then runs the loader. Run monthly (systemd timer
on the 3rd — gives Tardis time to publish).

Free tier only, no API key. Paid full-month backfill is a separate
decision (see TODO).
"""

import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

TARDIS_DIR = os.path.join(BASE_DIR, 'warehouse', 'tardis')
os.makedirs(TARDIS_DIR, exist_ok=True)

TARGETS = [
    ('gate-io', 'KAS_USDT'), ('gate-io', 'CLORE_USDT'),
    ('gate-io', 'FLUX_USDT'), ('gate-io', 'AKT_USDT'),
    ('mexc', 'NOCKUSDT'), ('mexc', 'NOSUSDT'), ('mexc', 'KASUSDT'),
    ('mexc', 'CLOREUSDT'), ('mexc', 'FLUXUSDT'),
]
DTYPES = ['trades', 'book_snapshot_25']


def month_firsts(n=4):
    """Last n month-firsts including current month (YYYY/MM/01)."""
    now = datetime.now(timezone.utc)
    out = []
    y, m = now.year, now.month
    for _ in range(n):
        out.append(f"{y:04d}/{m:02d}/01")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return out


def main():
    new = 0
    for month in month_firsts():
        for ex, sym in TARGETS:
            for dtype in DTYPES:
                fn = f"{ex}_{sym}_{dtype}_{month.replace('/', '')}.csv.gz"
                fp = os.path.join(TARDIS_DIR, fn)
                if os.path.exists(fp):
                    continue
                url = f'https://datasets.tardis.dev/v1/{ex}/{dtype}/{month}/{sym}.csv.gz'
                try:
                    req = urllib.request.Request(
                        url, headers={'User-Agent': 'PowPowPow/1.0'})
                    data = urllib.request.urlopen(req, timeout=60).read()
                    with open(fp, 'wb') as fh:
                        fh.write(data)
                    print(f"  OK {fn} {len(data)/1e6:.1f}MB", flush=True)
                    new += 1
                except Exception as e:
                    print(f"  miss {fn} ({str(e)[:60]})", flush=True)
    if new:
        print(f"[DRIP] +{new} new files, loading...")
        subprocess.run([sys.executable,
                        os.path.join(BASE_DIR, 'scripts', 'load_tardis.py')],
                       check=False)
    else:
        print("[DRIP] nothing new")


if __name__ == '__main__':
    main()
