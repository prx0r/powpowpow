from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any
from enum import Enum
import hashlib
import json

class TruthClass(Enum):
    """How much evidence backs this record."""
    VERIFIED = "verified"       # directly measured, provenance clear
    DERIVED = "derived"         # computed from verified observations
    ESTIMATED = "estimated"     # computed with assumptions
    HEURISTIC = "heuristic"     # rule of thumb, not calibrated
    CONCEPTUAL = "conceptual"   # architecture only, no data
    UNAVAILABLE = "unavailable" # data not yet collected

class Recoverability(Enum):
    """Can this observation be recreated from external sources?"""
    CANONICAL = "canonical"           # chain/explorer APIs can rebuild
    THIRD_PARTY = "third_party"       # external services retain this
    PARTIAL = "partial"               # some components recoverable
    EPHEMERAL = "ephemeral"           # CANNOT reconstruct — archive continuously

@dataclass
class Observation:
    """A raw, immutable record from reality.

    Every observation has:
    - What was observed (entity, metric, value)
    - When it was true (event_time)
    - When we observed it (observed_at)
    - Where it came from (source_id)
    - How confident we are (truth_class)
    - A deterministic ID (observation_id)
    """
    # Identity
    observation_id: str          # deterministic hash
    entity_id: str               # what was observed
    garden: str                  # which garden this belongs to

    # What
    metric: str                  # what was measured
    value: Any                   # the observation
    
    # When
    event_time: str              # when this was true in reality (ISO UTC)
    observed_at: str             # when we observed it (ISO UTC)

    # Where from
    source_id: str               # which source produced this
    unit: str = ""
    
    # Quality (all optional fields with defaults at the end)
    source_version: str = "1.0"
    truth_class: TruthClass = TruthClass.ESTIMATED
    recoverability: Recoverability = Recoverability.THIRD_PARTY
    
    # Provenance
    parent_observation_ids: list = field(default_factory=list)  # if derived
    method_id: str = ""          # which method produced this
    method_version: str = ""
    
    # Metadata
    tags: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.observation_id:
            self.observation_id = self._compute_id()

    def _compute_id(self) -> str:
        """Deterministic ID from content."""
        content = json.dumps({
            "entity_id": self.entity_id,
            "garden": self.garden,
            "metric": self.metric,
            "event_time": self.event_time,
            "source_id": self.source_id,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "entity_id": self.entity_id,
            "garden": self.garden,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "event_time": self.event_time,
            "observed_at": self.observed_at,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "truth_class": self.truth_class.value,
            "recoverability": self.recoverability.value,
            "parent_observation_ids": self.parent_observation_ids,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "tags": self.tags,
        }
