from dataclasses import dataclass, field
from core.observation import TruthClass

@dataclass
class BreadupValuation:
    """A valuation of a physical object with full evidence chain.
    
    This is what Breadup's value_listing() should produce and store.
    It captures not just the answer but how we got there.
    """
    valuation_id: str
    item_query: str           # what was asked about
    entity_id: str            # resolved entity (if found)
    
    # Market data
    asking_price: float = 0
    platform: str = ""
    
    # Comparable sales
    n_comps: int = 0          # number of comparable sales found
    median_sold: float = 0
    p25_sold: float = 0
    p75_sold: float = 0
    min_sold: float = 0
    max_sold: float = 0
    
    # Evidence quality
    comp_age_days_p50: float = 0  # median age of comps
    condition_match_rate: float = 0  # % matching target condition
    source_observations: list = field(default_factory=list)  # observation IDs
    
    # Verdict
    verdict: str = ""         # BARGAIN / FAIR / OVERPRICED / NO_DATA
    suggested_offer: float = 0
    
    # Cost model (for max_offer)
    platform_fee_pct: float = 0
    estimated_postage: float = 0
    estimated_total_cost: float = 0
    
    # Temporal
    as_of: str = ""           # when this valuation was true
    computed_at: str = ""     # when we computed it
    
    # Quality
    truth_class: TruthClass = TruthClass.ESTIMATED
    confidence: float = 0
    method_id: str = "breadup_valuation"
    method_version: str = "0.2.0"
    limitations: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {k: v.value if hasattr(v, 'value') else v 
                for k, v in self.__dict__.items()}
