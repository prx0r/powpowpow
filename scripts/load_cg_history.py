"""
CoinGecko 365d history loader — the outcome variable.

market_chart per coin (prices + total_volumes, daily) → normalized
price_history rows with exchange_time = day UTC. Feeds backtests and
Seesaw lag analysis (price vs difficulty/hashrate). Free tier: sleep
between coins to respect rate limits; failures archived via core.

Usage:
    python3 scripts/load_cg_history.py
    python3 scripts/load_cg_history.py --coins XMR,QUBIC,PRL --days 90
"""

import argparse
import sys
import time
from datetime import datetime, timezone
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

CG_IDS = {
    'XMR': 'monero',
    'QUBIC': 'qubic-network',
    'PRL': 'pearl-2',
    'KAS': 'kaspa',
    'NOCK': 'nockchain',
    'XEL': 'xelis',
    'XTM': 'minotari',
    'NOS': 'nosana',
    'AKT': 'akash-network',
    'TAO': 'bittensor',
    'FLUX': 'flux',
    'CLORE': 'clore-ai',
}


def load_coin(sym, cg_id, days=365):
    data = fetch_json(
        f'https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart',
        params={'vs_currency': 'usd', 'days': days},
        source_id='coingecko', chain_id=sym.lower())
    if not data or not isinstance(data.get('prices'), list):
        print(f"  [{sym}] no data (wrong id? rate limit?)")
        return 0
    vols = {int(t): v for t, v in (data.get('total_volumes') or [])}
    n = 0
    for t_ms, price in data['prices']:
        day = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
        store_normalized('price_history', sym.lower(), {
            'symbol': sym, 'date': day,
            'exchange_time': datetime.fromtimestamp(
                t_ms / 1000, tz=timezone.utc).isoformat(),
            'close_usd': price, 'volume_usd': vols.get(int(t_ms)),
            'source_role': 'derived', 'source_id': 'coingecko',
        }, event_time=day)
        n += 1
    print(f"  [{sym}] +{n} daily closes")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--coins', default=None)
    ap.add_argument('--days', type=int, default=365)
    args = ap.parse_args()
    coins = args.coins.split(',') if args.coins else sorted(CG_IDS)
    print(f"[CG] {utcnow()}")
    total = 0
    for i, sym in enumerate(coins):
        cg_id = CG_IDS.get(sym.upper())
        if not cg_id:
            print(f"  [{sym}] no coingecko id mapped")
            continue
        try:
            total += load_coin(sym.upper(), cg_id, args.days)
        except Exception as e:
            print(f"  [{sym}] ERR {str(e)[:120]}")
        if i < len(coins) - 1:
            time.sleep(12)  # free-tier courtesy
    print(f"[CG] +{total} price rows")


if __name__ == '__main__':
    main()
