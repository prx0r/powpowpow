"""
DataGarden — Universal Schema
Normalized schema for all chain data regardless of source.

Bitemporal: every record carries observed_at and valid_from for
point-in-time correctness in backtests.

NOTE: These are the PowPowPow-specific types from the original implementation.
The new core/ module has the garden-agnostic types.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Recoverability classification
RECOVERABILITY = {
    'canonical_reconstructable': 'chain/explorer APIs can rebuild this',
    'third_party_reconstructable': 'external services retain this',
    'partially_reconstructable': 'some components recoverable, some not',
    'ephemeral': 'CANNOT reconstruct later — archive continuously',
}

@dataclass
class BitemporalMixin:
    """Bitemporal metadata for point-in-time correctness."""
    observed_at: str  # when observed
    valid_from: str   # when this was true in the real world
    valid_to: Optional[str] = None  # when this stopped being true
    recoverability: str = 'unknown'  # RECOVERABILITY key
    source_id: str = 'unknown'
    source_version: str = '1.0'
    superseded_by: Optional[str] = None  # entity_id of newer observation

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
class MiningPoolSnapshot:
    """Mining pool telemetry — the strongest missing layer."""
    pool_id: str
    network: str
    event_time: str

    pool_hashrate: Optional[float] = None
    network_hashrate: Optional[float] = None
    miner_count: Optional[int] = None
    worker_count: Optional[int] = None

    pool_difficulty: Optional[float] = None
    payout_scheme: Optional[str] = None
    pool_fee: Optional[float] = None
    minimum_payout: Optional[float] = None

    blocks_24h: Optional[int] = None
    expected_blocks_24h: Optional[float] = None
    observed_effort: Optional[float] = None

    payouts_native_24h: Optional[float] = None

@dataclass
class StratumJob:
    """Stratum job observation — machines joining/leaving before hashrate reflects it."""
    pool: str
    received_at: str

    job_id: Optional[str] = None
    chain_height: Optional[int] = None
    target: Optional[str] = None
    difficulty: Optional[float] = None

    job_interval_ms: Optional[float] = None
    reconnect: Optional[bool] = None
    stale_job: Optional[bool] = None

@dataclass
class GPUAvailability:
    """GPU market observation — availability matters more than price alone."""
    timestamp: str

    gpu_model: Optional[str] = None
    provider: Optional[str] = None
    region: Optional[str] = None

    price_usd_gpu_hour: Optional[float] = None
    pricing_type: Optional[str] = None  # spot, on-demand, reserved

    availability: Optional[str] = None  # available, limited, unavailable, stale
    available_units: Optional[int] = None
    node_size: Optional[str] = None

    provider_count: Optional[int] = None

@dataclass
class HardwareLeadTime:
    """Hardware supply quote — physical lag in supply response."""
    timestamp: str
    hardware_model: str

    unit_price: Optional[float] = None
    quantity_available: Optional[int] = None
    condition: Optional[str] = None  # new, refurbished, used

    region: Optional[str] = None
    lead_time_days: Optional[int] = None

    source: Optional[str] = None

@dataclass
class PowerMarket:
    """Electricity constraint prices — shadow prices of physical constraints."""
    event_time: str

    grid: Optional[str] = None
    node: Optional[str] = None
    region: Optional[str] = None

    lmp_usd_mwh: Optional[float] = None

    energy_component: Optional[float] = None
    congestion_component: Optional[float] = None
    loss_component: Optional[float] = None

    constraint_id: Optional[str] = None
    constraint_shadow_price: Optional[float] = None

    demand: Optional[float] = None
    generation: Optional[float] = None

@dataclass
class ExchangeTick:
    """Cross-exchange tick — where information appears first."""
    timestamp: str
    asset: str
    exchange: str

    mid: Optional[float] = None
    spread: Optional[float] = None
    depth_1pct: Optional[float] = None
    ofi: Optional[float] = None  # order flow imbalance
    aggressive_flow: Optional[float] = None

@dataclass
class PoolMigration:
    """Pool share and migration signal."""
    network: str
    timestamp: str

    pool_id: str
    pool_share: Optional[float] = None
    miner_count: Optional[int] = None
    worker_count: Optional[int] = None
    block_share: Optional[float] = None
    payout_volume: Optional[float] = None

    hhi: Optional[float] = None  # Herfindahl-Hirschman Index

@dataclass
class MinerSoftwareRelease:
    """Mining software version — acts like sudden hardware creation."""
    released_at: str
    network: str
    software: str
    version: str

    commit: Optional[str] = None
    hardware: Optional[str] = None
    benchmark_before: Optional[float] = None
    benchmark_after: Optional[float] = None
    power_before: Optional[float] = None
    power_after: Optional[float] = None

@dataclass
class ASICQuote:
    """ASIC market pricing — capital pressure signal."""
    timestamp: str

    manufacturer: Optional[str] = None
    model: Optional[str] = None
    algo: Optional[str] = None

    hashrate: Optional[float] = None
    power: Optional[float] = None

    price: Optional[float] = None
    release_date: Optional[str] = None

@dataclass
class ProbeObservation:
    """Active network probe — information propagation measurement."""
    probe_id: str
    probe_region: str
    target: str
    request_sent_at: str

    first_byte_at: Optional[str] = None
    event_received_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

@dataclass
class ProtocolParameter:
    """Protocol rule change — structural breaks in metrics."""
    event_time: str
    network: str

    parameter: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    activation_height: Optional[int] = None
    source_commit: Optional[str] = None

@dataclass
class ResourceOpportunitySnapshot:
    """What could a machine rationally have done at this exact moment?
    
    The purest Seesaw table: opportunity cost of resource allocation.
    In a year you can reconstruct:
    "What could an H100 rationally have done at this exact moment?"
    """
    event_time: str
    hardware_class: str  # H100, H200, A100, RTX_4090, CPU_XMR, etc.

    network: str
    activity_type: str  # mine / rent / inference / idle

    gross_usd_hour: Optional[float] = None
    energy_usd_hour: Optional[float] = None
    fees_usd_hour: Optional[float] = None
    net_usd_hour: Optional[float] = None

    confidence: Optional[float] = None  # 0-1, data quality
    source_observations: List[str] = field(default_factory=list)

    # Derived fields (computed, not stored raw)
    opportunity_set_rank: Optional[int] = None  # rank among alternatives
    allocation_regret: Optional[float] = None   # best alternative - chosen

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

def pool_snapshot_to_dict(pool: MiningPoolSnapshot) -> Dict[str, Any]:
    """Convert mining pool snapshot to dictionary."""
    return {
        'pool_id': pool.pool_id,
        'network': pool.network,
        'event_time': pool.event_time,
        'pool_hashrate': pool.pool_hashrate,
        'network_hashrate': pool.network_hashrate,
        'miner_count': pool.miner_count,
        'worker_count': pool.worker_count,
        'pool_difficulty': pool.pool_difficulty,
        'payout_scheme': pool.payout_scheme,
        'pool_fee': pool.pool_fee,
        'minimum_payout': pool.minimum_payout,
        'blocks_24h': pool.blocks_24h,
        'expected_blocks_24h': pool.expected_blocks_24h,
        'observed_effort': pool.observed_effort,
        'payouts_native_24h': pool.payouts_native_24h,
    }

def stratum_job_to_dict(job: StratumJob) -> Dict[str, Any]:
    """Convert stratum job to dictionary."""
    return {
        'pool': job.pool,
        'received_at': job.received_at,
        'job_id': job.job_id,
        'chain_height': job.chain_height,
        'target': job.target,
        'difficulty': job.difficulty,
        'job_interval_ms': job.job_interval_ms,
        'reconnect': job.reconnect,
        'stale_job': job.stale_job,
    }

def gpu_availability_to_dict(gpu: GPUAvailability) -> Dict[str, Any]:
    """Convert GPU availability to dictionary."""
    return {
        'timestamp': gpu.timestamp,
        'gpu_model': gpu.gpu_model,
        'provider': gpu.provider,
        'region': gpu.region,
        'price_usd_gpu_hour': gpu.price_usd_gpu_hour,
        'pricing_type': gpu.pricing_type,
        'availability': gpu.availability,
        'available_units': gpu.available_units,
        'node_size': gpu.node_size,
        'provider_count': gpu.provider_count,
    }

def power_market_to_dict(pm: PowerMarket) -> Dict[str, Any]:
    """Convert power market observation to dictionary."""
    return {
        'event_time': pm.event_time,
        'grid': pm.grid,
        'node': pm.node,
        'region': pm.region,
        'lmp_usd_mwh': pm.lmp_usd_mwh,
        'energy_component': pm.energy_component,
        'congestion_component': pm.congestion_component,
        'loss_component': pm.loss_component,
        'constraint_id': pm.constraint_id,
        'constraint_shadow_price': pm.constraint_shadow_price,
        'demand': pm.demand,
        'generation': pm.generation,
    }

def exchange_tick_to_dict(tick: ExchangeTick) -> Dict[str, Any]:
    """Convert exchange tick to dictionary."""
    return {
        'timestamp': tick.timestamp,
        'asset': tick.asset,
        'exchange': tick.exchange,
        'mid': tick.mid,
        'spread': tick.spread,
        'depth_1pct': tick.depth_1pct,
        'ofi': tick.ofi,
        'aggressive_flow': tick.aggressive_flow,
    }

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
