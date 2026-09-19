"""
PowPowPow Core — Canonical Seesaw Panel

Single research table that everything downstream uses.
No custom datasets — everything queries this panel.

seesaw_panel_1h / seesaw_panel_1d
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

PANEL_DIR = '/home/box/powpowpow/core/panel'


def _ensure_dir():
    os.makedirs(PANEL_DIR, exist_ok=True)


def store_panel_record(
    panel_type: str,  # '1h' or '1d'
    timestamp: str,
    asset: str,
    record: dict,
) -> str:
    """Store a panel record."""
    _ensure_dir()

    panel_dir = os.path.join(PANEL_DIR, f"seesaw_panel_{panel_type}")
    os.makedirs(panel_dir, exist_ok=True)

    asset_dir = os.path.join(panel_dir, f"asset={asset}")
    os.makedirs(asset_dir, exist_ok=True)

    ts = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
    date_dir = os.path.join(asset_dir, f"date={ts:%Y-%m-%d}")
    os.makedirs(date_dir, exist_ok=True)

    filepath = os.path.join(date_dir, f"hour={ts:%H}.jsonl")

    full_record = {
        'timestamp': timestamp,
        'asset': asset,
        **record,
    }

    with open(filepath, 'a') as f:
        f.write(json.dumps(full_record, default=str) + '\n')

    return filepath


def read_panel(
    panel_type: str,
    asset: str = None,
    start_date: str = None,
    end_date: str = None,
) -> List[dict]:
    """Read panel records."""
    panel_dir = os.path.join(PANEL_DIR, f"seesaw_panel_{panel_type}")
    if not os.path.exists(panel_dir):
        return []

    results = []

    if asset:
        asset_dirs = [os.path.join(panel_dir, f"asset={asset}")]
    else:
        asset_dirs = [os.path.join(panel_dir, d) for d in os.listdir(panel_dir)
                      if d.startswith('asset=')]

    for asset_dir in asset_dirs:
        if not os.path.exists(asset_dir):
            continue

        for date_dir_name in sorted(os.listdir(asset_dir)):
            if not date_dir_name.startswith('date='):
                continue
            date_str = date_dir_name.replace('date=', '')

            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue

            date_dir = os.path.join(asset_dir, date_dir_name)
            for fname in sorted(os.listdir(date_dir)):
                if fname.endswith('.jsonl'):
                    with open(os.path.join(date_dir, fname)) as f:
                        for line in f:
                            if line.strip():
                                results.append(json.loads(line))

    return sorted(results, key=lambda r: r.get('timestamp', ''))


# ============================================================
# Panel column definitions
# ============================================================

PANEL_COLUMNS = {
    # Identity
    'timestamp': 'ISO timestamp',
    'asset': 'Asset symbol',

    # Market
    'price': 'Price',
    'return_1d': '1-day return',
    'return_5d': '5-day return',
    'volume': '24h volume',
    'market_cap': 'Market cap',

    # Broad market
    'btc_return': 'BTC return',
    'btc_volatility': 'BTC 20d vol',
    'eth_return': 'ETH return',
    'crypto_market_return': 'BTC-weighted market return',
    'crypto_market_volatility': 'Market vol',

    # BTC-adjusted
    'btc_beta_7d': 'Rolling 7d BTC beta',
    'btc_beta_30d': 'Rolling 30d BTC beta',
    'btc_beta_90d': 'Rolling 90d BTC beta',
    'residual_return': 'Return unexplained by BTC',
    'residual_volatility': 'Idiosyncratic vol',

    # Physical network
    'hashrate': 'Network hashrate',
    'difficulty': 'Difficulty',
    'capacity': 'Active mining capacity',
    'emission_daily': 'Daily token emission',
    'emission_usd': 'Daily emission in USD',
    'block_reward': 'Block reward',
    'block_time_avg': 'Average block time',

    # Economics
    'revenue_per_resource': 'Revenue per unit resource',
    'electricity_cost': 'Electricity cost per unit',
    'external_resource_value': 'External opportunity cost',
    'allocation_wedge': 'Protocol - external return',
    'miner_margin': 'Net mining margin',
    'miner_sell_burden': 'Emission × sell fraction',
    'absorption_ratio': 'Volume / emission',

    # Liquidity
    'spread': 'Bid-ask spread',
    'spread_pct': 'Spread as % of price',
    'depth_usd': 'Total depth within 5%',
    'ofi': 'Order flow imbalance',
    'aggressive_flow': 'Net aggressive buys',
    'bid_depth': 'Total bid depth',
    'ask_depth': 'Total ask depth',

    # Resource markets
    'gpu_rental_price': 'H100 rental $/hour',
    'gpu_availability': 'Available GPU units',
    'gpu_stockout': 'Stockout indicator',
    'energy_price': 'Electricity $/kWh',
    'hardware_lead_time_days': 'GPU delivery lead time',

    # Event state
    'protocol_event': 'Protocol event flag',
    'listing_event': 'Exchange listing event',
    'software_event': 'Software release event',
    'event_importance': 'Event importance score',
}

if __name__ == '__main__':
    print("Seesaw panel columns:")
    for col, desc in PANEL_COLUMNS.items():
        print(f"  {col:35} {desc}")

    print(f"\nTotal: {len(PANEL_COLUMNS)} columns")
