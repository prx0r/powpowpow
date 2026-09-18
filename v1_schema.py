"""
PowPowPow V1 Schema Standard
All 8 chains use this exact schema.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ============================================================
# RAW EVENT SCHEMA
# ============================================================

@dataclass
class RawEvent:
    """Immutable raw event from any source."""
    observed_at: str                    # ISO timestamp
    chain_id: str                       # PRL, QUBIC, etc.
    source_id: str                      # rpc, websocket, explorer, etc.
    source_type: str                    # rpc | websocket | grpc | rest
    source_version: str                 # API version
    endpoint: str                       # Full URL called
    request_params: Dict[str, Any]      # Query params
    raw_payload: Any                    # Original response
    payload_hash: str                   # SHA256 of payload
    node_height: Optional[int]          # Chain height at observation
    node_tip_hash: Optional[str]        # Block hash at observation
    ingest_version: str                 # Our pipeline version

# ============================================================
# CHAIN SNAPSHOT (Normalized)
# ============================================================

@dataclass
class ChainSnapshot:
    """Normalized chain state at a point in time."""
    timestamp: str
    chain: str                          # PRL, QUBIC, etc.
    height: Optional[int] = None
    difficulty: Optional[float] = None
    hashrate: Optional[float] = None
    hashrate_unit: Optional[str] = None
    block_reward: Optional[float] = None
    block_time_avg: Optional[float] = None
    tx_count_24h: Optional[int] = None
    fees_24h: Optional[float] = None
    mempool_tx_count: Optional[int] = None
    peer_count: Optional[int] = None
    version: Optional[str] = None

# ============================================================
# HARDWARE BENCHMARK
# ============================================================

@dataclass
class HardwareBenchmark:
    """Hardware performance on a specific chain."""
    timestamp: str
    chain: str
    algorithm: str
    hardware_type: str                  # cpu, gpu, asic
    hardware_model: str                 # H100, Ryzen 9, KS5, etc.
    hashrate: float                     # H/s
    power_watts: float
    cost_usd: float                     # Purchase price
    efficiency: Optional[float] = None  # H/s per watt
    source: str                         # Where benchmark came from
    source_url: Optional[str] = None

# ============================================================
# MINER ECONOMICS
# ============================================================

@dataclass
class MinerEconomics:
    """Economics for a hardware type on a chain."""
    timestamp: str
    chain: str
    hardware_model: str
    
    # Revenue
    coins_per_day: float
    revenue_usd_day: float
    
    # Costs
    electricity_usd_day: float
    hardware_amort_usd_day: float
    pool_fee_pct: Optional[float] = None
    total_cost_usd_day: Optional[float] = None
    
    # Profit
    gross_margin_usd_day: Optional[float] = None
    net_profit_usd_day: Optional[float] = None
    payback_days: Optional[float] = None
    
    # Network context
    network_hashrate: Optional[float] = None
    difficulty: Optional[float] = None
    network_share_pct: Optional[float] = None

# ============================================================
# SUPPLIER SNAPSHOT
# ============================================================

@dataclass
class SupplierSnapshot:
    """State of a single supplier/provider."""
    timestamp: str
    chain: str
    supplier_id: str
    
    # Resource
    resource_type: str                  # gpu, cpu, asic
    hardware_model: Optional[str] = None
    hardware_count: Optional[int] = None
    
    # Capacity
    capacity_total: Optional[float] = None
    capacity_available: Optional[float] = None
    capacity_active: Optional[float] = None
    
    # Economics
    ask_price_usd: Optional[float] = None
    realized_price_usd: Optional[float] = None
    protocol_reward_native: Optional[float] = None
    protocol_reward_usd: Optional[float] = None
    
    # Status
    online: Optional[bool] = None
    uptime_pct: Optional[float] = None

# ============================================================
# MARKET SNAPSHOT
# ============================================================

@dataclass
class MarketSnapshot:
    """Token market data."""
    timestamp: str
    chain: str
    
    price_usd: float
    market_cap: Optional[float] = None
    fdv: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    
    # SafeTrade specific
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread_bps: Optional[float] = None
    bid_depth_5pct: Optional[float] = None
    ask_depth_5pct: Optional[float] = None

# ============================================================
# RESOURCE MARKET (For CLORE, AKT, NOS)
# ============================================================

@dataclass
class ResourceMarket:
    """GPU/CPU marketplace state."""
    timestamp: str
    network: str
    
    # Capacity
    total_capacity: Optional[int] = None
    available_capacity: Optional[int] = None
    active_capacity: Optional[int] = None
    utilization_pct: Optional[float] = None
    
    # Pricing
    median_ask_usd: Optional[float] = None
    avg_realized_usd: Optional[float] = None
    
    # Supply
    supplier_count: Optional[int] = None
    hhi: Optional[float] = None  # Herfindahl index
    
    # Demand
    jobs_active: Optional[int] = None
    jobs_completed_24h: Optional[int] = None
    queue_length: Optional[int] = None

# ============================================================
# LIVE CARD
# ============================================================

@dataclass
class LiveCard:
    """Human-readable profitability card."""
    coin: str
    timestamp: str
    hardware: str
    
    # Revenue
    gross_revenue_day: float
    electricity_day: float
    hardware_amort_day: float
    net_profit_day: float
    
    # Network
    hashrate_change_7d: Optional[float] = None
    difficulty_change_7d: Optional[float] = None
    miner_issuance_usd_day: Optional[float] = None
    pool_to_exchange_usd_day: Optional[float] = None
    
    # Order book
    bid_depth_5pct: Optional[float] = None
    required_absorption_usd_day: Optional[float] = None
    
    # Price
    price_usd: Optional[float] = None
    payback_days: Optional[float] = None

def to_dict(obj) -> Dict[str, Any]:
    """Convert dataclass to dict."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    return obj.__dict__ if hasattr(obj, '__dict__') else {}
