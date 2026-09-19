from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .observation import TruthClass

@dataclass
class DerivedFact:
    """A fact computed from observations.

    DerivedFacts are never raw data. They always have:
    - A method that produced them
    - Input observation IDs
    - A version (so the same inputs can be reprocessed)
    - A truth class
    """
    derived_id: str              # deterministic hash
    garden: str
    entity_id: str
    metric: str
    value: Any
    method_id: str               # which method

    unit: str = ""
    method_version: str = ""
    input_observation_ids: list = field(default_factory=list)

    # Quality
    truth_class: TruthClass = TruthClass.DERIVED
    confidence: float = 0.0      # 0-1, calibrated

    # When
    computed_at: str = ""        # ISO UTC
    valid_from: str = ""         # when this became true
    valid_to: str = ""           # when this stopped being true

    # Evidence chain
    limitations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v.value if isinstance(v, Enum) else v 
                for k, v in self.__dict__.items()}
