from dataclasses import dataclass, field
from enum import Enum

class OutcomeStatus(Enum):
    PENDING = "pending"           # not yet resolved
    SUCCESS = "success"           # worked as expected
    PARTIAL = "partial"           # partly worked
    FAILURE = "failure"           # didn't work
    CANCELLED = "cancelled"       # user cancelled
    SUPERSEDED = "superseded"     # replaced by newer outcome

@dataclass
class Outcome:
    """What actually happened after a capability was used.

    This is the feedback loop. The whole thesis depends on
    predictions/actions resolving later. Design this contract now.
    """
    outcome_id: str
    capability_result_id: str     # which capability result this resolves

    # What happened
    status: OutcomeStatus = OutcomeStatus.PENDING
    actual_result: dict = field(default_factory=dict)

    # Comparison
    predicted_vs_actual: dict = field(default_factory=dict)  # {metric: {predicted, actual, error}}

    # Feedback
    user_feedback: str = ""       # what the user said/did
    user_satisfaction: float = 0.0  # 0-1 if available

    # When
    initiated_at: str = ""        # ISO UTC
    resolved_at: str = ""         # ISO UTC

    # Evidence
    resolution_evidence: list = field(default_factory=list)  # observation IDs

    def to_dict(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "capability_result_id": self.capability_result_id,
            "status": self.status.value,
            "actual_result": self.actual_result,
            "predicted_vs_actual": self.predicted_vs_actual,
            "user_feedback": self.user_feedback,
            "user_satisfaction": self.user_satisfaction,
            "initiated_at": self.initiated_at,
            "resolved_at": self.resolved_at,
            "resolution_evidence": self.resolution_evidence,
        }
