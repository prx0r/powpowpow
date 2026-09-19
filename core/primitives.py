"""
PowPowPow Core — Domain-Agnostic Resource/Constraint Primitives

These are the shared primitives across all verticals:
GPU cloud, PoW networks, semiconductors, energy, agent compute.

Every vertical maps into these primitives.
Cross-layer Seesaws emerge from the joins.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# ============================================================
# PRIMITIVE: Resource
# ============================================================

@dataclass
class Resource:
    """A scarce physical or computational resource."""
    resource_id: str          # stable permanent ID
    resource_type: str        # compute, memory, energy, networking, fabrication, cooling
    name: str
    unit: str                 # gpu_hour, mwh, gb_hbm3e, etc.

    substitutes: List[str] = field(default_factory=list)  # resource_ids
    parent_resource: Optional[str] = None  # e.g., h100 depends on hbm3e
    domain: str = ''          # pow, gpu_cloud, semiconductors, energy, agents


@dataclass
class Supplier:
    """An entity that provides a resource."""
    supplier_id: str
    resource_id: str
    name: str
    region: str = ''
    supplier_type: str = ''   # pool, cloud_provider, manufacturer, miner, grid

    hardware_types: List[str] = field(default_factory=list)
    payment_assets: List[str] = field(default_factory=list)
    first_seen: str = ''
    last_seen: str = ''


# ============================================================
# PRIMITIVE: Capacity & Utilization
# ============================================================

@dataclass
class CapacityObservation:
    """Physical capacity of a resource at a point in time."""
    resource_id: str
    timestamp: str

    total_capacity: Optional[float] = None
    active_capacity: Optional[float] = None
    available_capacity: Optional[float] = None
    pending_capacity: Optional[float] = None

    utilization_pct: Optional[float] = None

    supplier_id: Optional[str] = None
    hardware_model: Optional[str] = None
    region: Optional[str] = None

    source_id: str = 'unknown'
    recoverability: str = 'ephemeral'


# ============================================================
# PRIMITIVE: Price Quote
# ============================================================

@dataclass
class PriceQuote:
    """Price observation for a resource."""
    resource_id: str
    timestamp: str

    price: float
    currency: str = 'USD'
    unit: str = ''            # per_hour, per_day, per_unit

    quote_type: str = ''      # spot, on_demand, reserved, bid, ask
    venue: str = ''           # exchange, marketplace, provider

    depth_usd: Optional[float] = None
    spread: Optional[float] = None

    source_id: str = 'unknown'
    recoverability: str = 'ephemeral'


# ============================================================
# PRIMITIVE: Lead Time & Inventory
# ============================================================

@dataclass
class LeadTimeObservation:
    """Hardware supply constraint."""
    resource_id: str
    timestamp: str

    hardware_model: str
    lead_time_days: Optional[int] = None
    quantity_available: Optional[int] = None
    quantity_on_order: Optional[int] = None

    unit_price: Optional[float] = None
    condition: str = ''       # new, refurbished, used
    region: str = ''

    source_id: str = 'unknown'
    recoverability: str = 'high'  # listings disappear


@dataclass
class InventorySnapshot:
    """Current inventory/availability state."""
    resource_id: str
    timestamp: str

    available_units: Optional[int] = None
    total_units: Optional[int] = None
    status: str = ''          # available, limited, unavailable, stockout

    stockout_duration_hours: Optional[float] = None
    time_to_restock_hours: Optional[float] = None

    source_id: str = 'unknown'


# ============================================================
# PRIMITIVE: Demand & Constraint Events
# ============================================================

@dataclass
class DemandEvent:
    """Something that increased demand for a resource."""
    event_id: str
    resource_id: str
    timestamp: str

    demand_type: str = ''     # ai_model_launch, network_growth, protocol_change
    magnitude: Optional[float] = None
    description: str = ''

    source_id: str = 'unknown'


@dataclass
class ConstraintEvent:
    """A physical or economic constraint binding."""
    event_id: str
    resource_id: str
    timestamp: str

    constraint_type: str = '' # stockout, capacity_limit, lead_time_expansion, price_spike
    severity: float = 0.0     # 0-1
    duration_hours: Optional[float] = None

    affected_downstream: List[str] = field(default_factory=list)  # resource_ids
    description: str = ''

    source_id: str = 'unknown'


# ============================================================
# PRIMITIVE: Constraint Tightness (derived)
# ============================================================

@dataclass
class ConstraintState:
    """Derived measure of how tight a constraint is."""
    resource_id: str
    timestamp: str

    tightness: float = 0.0           # 0=slack, 1=maximum binding
    price_acceleration: float = 0.0  # d²price/dt²
    capacity_response: float = 0.0   # how fast supply is responding
    lead_time_change: float = 0.0    # expanding or contracting
    substitution_pressure: float = 0.0  # are alternatives emerging
    scarcity_persistence: float = 0.0    # how long has this been tight

    source_observations: List[str] = field(default_factory=list)


# ============================================================
# PRIMITIVE: Cross-Layer Seesaw
# ============================================================

@dataclass
class CrossLayerSeesaw:
    """Constraint migration across resource layers."""
    timestamp: str

    upstream_resource: str
    downstream_resource: str

    upstream_tightness: float = 0.0
    downstream_tightness: float = 0.0
    lag_days: Optional[float] = None

    migration_detected: bool = False
    confidence: float = 0.0


# ============================================================
# GEOGRAPHY
# ============================================================

@dataclass
class Region:
    """Geographic region with resource characteristics."""
    region_id: str
    name: str

    electricity_price_kwh: Optional[float] = None
    grid_constraint_id: Optional[str] = None
    datacenter_capacity_mw: Optional[float] = None
    gpu_density: Optional[float] = None


# ============================================================
# METHODOLOGY
# ============================================================

@dataclass
class Methodology:
    """How a metric was calculated. Version everything."""
    metric_id: str
    version: str

    formula: str
    inputs: Dict[str, str] = field(default_factory=dict)  # input_name -> version
    assumptions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    created_at: str = ''
    superseded_by: Optional[str] = None
