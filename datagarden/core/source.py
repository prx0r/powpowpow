from dataclasses import dataclass, field
from .observation import Recoverability

@dataclass
class Source:
    """A data source with metadata about its reliability.

    Every source states:
    - What it provides
    - How often it updates
    - Whether it can be reconstructed
    - Its current health
    """
    source_id: str               # unique identifier
    garden: str                  # which garden
    name: str                    # human-readable name
    source_type: str             # api, scrape, bulk_download, manual

    # Cadence
    expected_cadence: str        # e.g. "daily", "hourly", "on_demand"
    last_collected: str = ""     # ISO UTC
    next_expected: str = ""      # ISO UTC

    # Reliability
    recoverability: Recoverability = Recoverability.THIRD_PARTY
    health: str = "unknown"      # healthy, degraded, broken, unknown
    health_checked_at: str = ""

    # Terms
    cost: str = "free"           # free, freemium, paid
    requires_api_key: bool = False
    terms_url: str = ""
    licensing: str = "unknown"   # open, ogrl, research, commercial

    # Freshness
    freshness_sla_hours: int = 48  # how stale is acceptable
    current_staleness_hours: float = 0

    # Statistics
    total_observations: int = 0
    last_error: str = ""
    error_count: int = 0
