from dataclasses import dataclass, field
from enum import Enum
from .observation import TruthClass

class ActionClass(Enum):
    """What can be done with this result."""
    ADVISORY = "advisory"         # informational only
    AUTO = "auto"                # agent can execute fully
    APPROVAL_REQUIRED = "approval_required"  # needs human OK
    USER_HANDOFF = "user_handoff"  # human must do it
    UNSUPPORTED = "unsupported"   # can't handle this

@dataclass
class CapabilityResult:
    """Answer to a human question with full evidence lineage.

    This is the contract between gardens and consumers (Muse, YouTube, API).
    Every result must carry:
    - What was asked
    - What was answered
    - How confident we are
    - What evidence backs it
    - What can be done with it
    """
    result_id: str
    capability: str              # e.g. "breadup.value_listing"
    garden: str

    # The answer
    result: dict = field(default_factory=dict)

    # Quality
    truth_class: TruthClass = TruthClass.ESTIMATED
    confidence: float = 0.0

    # Evidence
    evidence_observation_ids: list = field(default_factory=list)
    evidence_derived_ids: list = field(default_factory=list)

    # Method
    method_id: str = ""
    method_version: str = ""

    # Action
    action_class: ActionClass = ActionClass.ADVISORY

    # When
    as_of: str = ""              # ISO UTC — when this was true
    computed_at: str = ""        # ISO UTC — when we computed it

    # Limitations
    limitations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "capability": self.capability,
            "garden": self.garden,
            "result": self.result,
            "truth_class": self.truth_class.value,
            "confidence": self.confidence,
            "evidence_observation_ids": self.evidence_observation_ids,
            "evidence_derived_ids": self.evidence_derived_ids,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "action_class": self.action_class.value,
            "as_of": self.as_of,
            "computed_at": self.computed_at,
            "limitations": self.limitations,
        }
