from dataclasses import dataclass, field
from core.observation import TruthClass, Recoverability

@dataclass
class HardwareEconomics:
    """Mining profitability observation for a specific hardware on a specific network.
    
    This is the type PowPowPow needs but doesn't have in its schema.
    It connects the physical hardware to the economic outcome.
    """
    observation_id: str
    device: str               # e.g. "RTX_4090", "ASIC_X19"
    algorithm: str            # e.g. "RandomX", "KawPow", "SHA256"
    symbol: str               # e.g. "XMR", "KAS", "BTC"
    
    # Hardware specs
    hashrate: float = 0       # H/s
    power_watts: float = 0
    hardware_cost_usd: float = 0
    
    # Economics
    revenue_usd_day: float = 0
    electricity_usd_day: float = 0
    electricity_rate: float = 0.10  # $/kWh
    net_profit_usd_day: float = 0
    payback_days: float = 0
    
    # Network context
    network_hashrate: float = 0
    network_difficulty: float = 0
    coin_price_usd: float = 0
    block_reward: float = 0
    
    # Temporal
    event_time: str = ""      # when this was true
    observed_at: str = ""     # when we observed it
    
    # Quality
    source_id: str = ""
    truth_class: TruthClass = TruthClass.DERIVED
    
    def to_dict(self) -> dict:
        return {k: v.value if hasattr(v, 'value') else v 
                for k, v in self.__dict__.items()}
