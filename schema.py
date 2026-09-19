import os
"""
PowPowPow — Universal Chain Schema
Normalized schema for all chain data regardless of source.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class ChainConfig:
    """Static chain configuration."""
    symbol: str
    name: str
    chain_type: str  # useful-compute, privacy, zk-pow, etc.
    consensus: str
    mining_algo: str
    max_supply: Optional[float] = None
    block_time: Optional[int] = None  # seconds
    useful_output: Optional[str] = None
    hardware_req: Optional[str] = None
    github_repo: Optional[str] = None
    github_stars: Optional[int] = None

@dataclass
class NetworkStats:
    """Live network statistics."""
    symbol: str
    timestamp: str
    height: Optional[int] = None
    hashrate: Optional[float] = None
    hashrate_unit: Optional[str] = None  # H/s, KH/s, MH/s, GH/s, TH/s, PH/s, EH/s
    difficulty: Optional[float] = None
    block_reward: Optional[float] = None
    block_time_avg: Optional[float] = None  # seconds
    tx_count_24h: Optional[int] = None
    active_addresses: Optional[int] = None
    mempool_size: Optional[int] = None

@dataclass
class EmissionData:
    """Token emission and inflation data."""
    symbol: str
    timestamp: str
    daily_emission: Optional[float] = None
    daily_emission_usd: Optional[float] = None
    annualized_emission: Optional[float] = None
    circulating_supply: Optional[float] = None
    dilution_pressure: Optional[float] = None  # annual emission / circulating
    emission_curve: Optional[str] = None  # linear, decay, halving, tail

@dataclass
class MinerData:
    """Mining economics data."""
    symbol: str
    timestamp: str
    miner_revenue_24h: Optional[float] = None
    miner_revenue_usd: Optional[float] = None
    fee_revenue_24h: Optional[float] = None
    sell_pressure_daily: Optional[float] = None
    sell_fraction: Optional[float] = None  # estimated % sold
    absorption_ratio: Optional[float] = None  # volume / emission
    pool_concentration: Optional[Dict[str, float]] = None  # pool -> share %

@dataclass
class MarketData:
    """Market and trading data."""
    symbol: str
    timestamp: str
    price: Optional[float] = None
    price_24h_change: Optional[float] = None
    market_cap: Optional[float] = None
    fdv: Optional[float] = None
    volume_24h: Optional[float] = None
    volume_24h_change: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

@dataclass
class OrderBookData:
    """L2 order book data."""
    symbol: str
    timestamp: str
    exchange: str
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    spread_pct: Optional[float] = None
    bid_depth_usd: Optional[float] = None
    ask_depth_usd: Optional[float] = None
    imbalance: Optional[float] = None  # -1 to 1

@dataclass
class GitHubData:
    """GitHub activity data."""
    symbol: str
    timestamp: str
    repo: str
    stars: Optional[int] = None
    forks: Optional[int] = None
    open_issues: Optional[int] = None
    commits_7d: Optional[int] = None
    commits_30d: Optional[int] = None
    active_developers: Optional[int] = None
    last_release: Optional[str] = None
    last_commit: Optional[str] = None

@dataclass
class ChainSnapshot:
    """Complete snapshot of all data for a chain."""
    symbol: str
    timestamp: str
    config: Optional[ChainConfig] = None
    network: Optional[NetworkStats] = None
    emission: Optional[EmissionData] = None
    miner: Optional[MinerData] = None
    market: Optional[MarketData] = None
    orderbook: Optional[OrderBookData] = None
    github: Optional[GitHubData] = None
    sources: List[str] = field(default_factory=list)
    data_quality: Dict[str, bool] = field(default_factory=dict)

def to_dict(snapshot: ChainSnapshot) -> Dict[str, Any]:
    """Convert snapshot to dictionary."""
    result = {
        'symbol': snapshot.symbol,
        'timestamp': snapshot.timestamp,
        'sources': snapshot.sources,
        'data_quality': snapshot.data_quality,
    }
    
    if snapshot.config:
        result['config'] = {
            'name': snapshot.config.name,
            'chain_type': snapshot.config.chain_type,
            'consensus': snapshot.config.consensus,
            'mining_algo': snapshot.config.mining_algo,
            'max_supply': snapshot.config.max_supply,
            'block_time': snapshot.config.block_time,
            'useful_output': snapshot.config.useful_output,
        }
    
    if snapshot.network:
        result['network'] = {
            'height': snapshot.network.height,
            'hashrate': snapshot.network.hashrate,
            'hashrate_unit': snapshot.network.hashrate_unit,
            'difficulty': snapshot.network.difficulty,
            'block_reward': snapshot.network.block_reward,
            'block_time_avg': snapshot.network.block_time_avg,
            'tx_count_24h': snapshot.network.tx_count_24h,
            'active_addresses': snapshot.network.active_addresses,
        }
    
    if snapshot.emission:
        result['emission'] = {
            'daily_emission': snapshot.emission.daily_emission,
            'daily_emission_usd': snapshot.emission.daily_emission_usd,
            'circulating_supply': snapshot.emission.circulating_supply,
            'dilution_pressure': snapshot.emission.dilution_pressure,
            'emission_curve': snapshot.emission.emission_curve,
        }
    
    if snapshot.miner:
        result['miner'] = {
            'revenue_24h_usd': snapshot.miner.miner_revenue_usd,
            'sell_pressure_daily': snapshot.miner.sell_pressure_daily,
            'absorption_ratio': snapshot.miner.absorption_ratio,
            'pool_concentration': snapshot.miner.pool_concentration,
        }
    
    if snapshot.market:
        result['market'] = {
            'price': snapshot.market.price,
            'market_cap': snapshot.market.market_cap,
            'fdv': snapshot.market.fdv,
            'volume_24h': snapshot.market.volume_24h,
        }
    
    if snapshot.github:
        result['github'] = {
            'repo': snapshot.github.repo,
            'stars': snapshot.github.stars,
            'commits_7d': snapshot.github.commits_7d,
            'active_developers': snapshot.github.active_developers,
        }
    
    return result
