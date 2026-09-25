"""
Chain Metrics Collector for PowPowPow
Fetches emission, hashrate, and miner data.
"""

import json
import os
import requests
from datetime import datetime

DATA_DIR = '/home/box/safetrade/tracked'
METRICS_DIR = os.path.join(BASE_DIR, 'data')

os.makedirs(METRICS_DIR, exist_ok=True)

# Coin configs
COINS = {
    'QUBIC': {
        'coingecko': 'qubic',
        'emission_per_day': 32_142_857_143,  # Approximate
        'max_supply': 200_000_000_000_000,
        'consensus': 'useful-pow',
    },
    'PRL': {
        'coingecko': 'pearl',
        'emission_per_day': 500_000,
        'max_supply': 2_100_000_000,
        'consensus': 'proof-of-useful-work',
    },
    'NOCK': {
        'coingecko': 'nockchain',
        'emission_per_day': 50_000,
        'max_supply': 4_294_967_296,
        'consensus': 'zk-pow',
    },
    'XMR': {
        'coingecko': 'monero',
        'emission_per_day': 432,  # Current Monero emission
        'max_supply': None,  # Tail emission
        'consensus': 'randomx',
    },
}

def fetch_coingecko_data(coin_id):
    """Fetch market data from CoinGecko."""
    try:
        url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
        params = {
            'localization': 'false',
            'tickers': 'false',
            'community_data': 'false',
            'developer_data': 'false'
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            market = data.get('market_data', {})
            return {
                'price_usd': market.get('current_price', {}).get('usd'),
                'market_cap': market.get('market_cap', {}).get('usd'),
                'volume_24h': market.get('total_volume', {}).get('usd'),
                'circulating_supply': market.get('circulating_supply'),
                'max_supply': market.get('max_supply'),
                'ath': market.get('ath', {}).get('usd'),
                'ath_change': market.get('ath_change_percentage', {}).get('usd'),
                'price_change_24h': market.get('price_change_percentage_24h'),
                'price_change_7d': market.get('price_change_percentage_7d'),
                'price_change_30d': market.get('price_change_percentage_30d'),
            }
    except Exception as e:
        print(f"  CoinGecko error: {e}")
    return None

def calculate_derived_metrics(coin, config, market_data):
    """Calculate PowPowPow-specific metrics."""
    metrics = {}
    
    if not market_data:
        return metrics
    
    # Emission metrics
    emission_per_day = config.get('emission_per_day', 0)
    emission_usd = emission_per_day * (market_data.get('price_usd', 0) or 0)
    
    metrics['emission_per_day'] = emission_per_day
    metrics['emission_usd_per_day'] = emission_usd
    
    # Miner sell burden (estimated)
    SELL_FRACTION = 0.6  # Assume miners sell 60%
    metrics['miner_sell_burden'] = emission_usd * SELL_FRACTION
    
    # Absorption ratio
    volume_24h = market_data.get('volume_24h', 0) or 0
    metrics['absorption_ratio'] = volume_24h / emission_usd if emission_usd else 0
    
    # Dilution pressure
    circulating = market_data.get('circulating_supply', 0) or 1
    max_supply = config.get('max_supply') or circulating * 1.5
    metrics['dilution_pressure'] = (emission_per_day * 365) / circulating if circulating else 0
    
    # Narrative premium (FDV vs market cap proxy)
    market_cap = market_data.get('market_cap', 0) or 0
    metrics['market_cap'] = market_cap
    metrics['fdv_proxy'] = market_cap * (max_supply / circulating) if circulating else market_cap
    
    return metrics

def collect_metrics():
    """Collect metrics for all tracked coins."""
    print(f"\n{'='*60}")
    print(f"Collecting Chain Metrics — {datetime.now()}")
    print(f"{'='*60}")
    
    all_metrics = {}
    
    for symbol, config in COINS.items():
        print(f"\n[{symbol}]")
        
        cg_id = config.get('coingecko')
        if cg_id:
            market_data = fetch_coingecko_data(cg_id)
            if market_data:
                print(f"  Price: ${market_data.get('price_usd', 0):.8f}")
                print(f"  Market Cap: ${market_data.get('market_cap', 0):,.0f}")
                print(f"  Volume 24h: ${market_data.get('volume_24h', 0):,.0f}")
            else:
                print("  No market data")
        else:
            market_data = None
        
        derived = calculate_derived_metrics(symbol, config, market_data)
        
        all_metrics[symbol] = {
            'timestamp': datetime.now().isoformat(),
            'market_data': market_data,
            'derived': derived,
            'config': config
        }
        
        if derived:
            print(f"  Emission: {derived.get('emission_per_day', 0):,.0f}/day (${derived.get('emission_usd_per_day', 0):,.0f})")
            print(f"  Absorption: {derived.get('absorption_ratio', 0):.2f}x")
            print(f"  Dilution: {derived.get('dilution_pressure', 0):.2%}/year")
    
    # Save
    output_file = os.path.join(METRICS_DIR, f'chain_metrics_{datetime.now():%Y%m%d}.json')
    with open(output_file, 'w') as f:
        json.dump(all_metrics, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    return all_metrics

if __name__ == '__main__':
    collect_metrics()
