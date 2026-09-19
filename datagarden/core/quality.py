"""Data Quality States.

Every observation and derived fact must have a quality state.
UNKNOWN is valuable — never silently turn missing data into FALSE.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

from .source_registry import SourceRegistry


class QualityState(Enum):
    """Quality state for every observation and derived fact.

    KNOWN      — directly observed, provenance clear
    INFERRED   — derived from known observations
    STALE      — exceeded freshness threshold for its source
    CONFLICTED — multiple sources disagree on this fact
    UNKNOWN    — no data available (valid, never replace with FALSE)
    """
    KNOWN = "KNOWN"
    INFERRED = "INFERRED"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class QualityAssessment:
    """Result of a quality check on an observation."""
    state: QualityState
    source_id: Optional[str]
    checked_at: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "source_id": self.source_id,
            "checked_at": self.checked_at,
            "reason": self.reason,
        }


class FreshnessChecker:
    """Checks if data is stale based on the source registry.

    Looks up the source, compares last_observed to max_age_hours,
    and returns a QualityState accordingly.
    """

    def __init__(self, registry: Optional[SourceRegistry] = None):
        self.registry = registry or SourceRegistry()

    def check(self, source_id: str, last_observed: Optional[datetime] = None) -> QualityAssessment:
        """Check freshness of a source.

        Args:
            source_id: identifier for the data source
            last_observed: when this data was last collected

        Returns:
            QualityAssessment with state set to KNOWN, STALE, or UNKNOWN
        """
        now = datetime.now(timezone.utc)

        result = self.registry.check_freshness(source_id, last_collected_at=last_observed)

        if result["status"] == "unknown":
            return QualityAssessment(
                state=QualityState.UNKNOWN,
                source_id=source_id,
                checked_at=now.isoformat(),
                reason="source not registered or no last_observed timestamp",
            )

        if result["is_fresh"]:
            return QualityAssessment(
                state=QualityState.KNOWN,
                source_id=source_id,
                checked_at=now.isoformat(),
                reason=f"within {result['max_age_hours']}h freshness window (age: {result['staleness_hours']}h)",
            )

        return QualityAssessment(
            state=QualityState.STALE,
            source_id=source_id,
            checked_at=now.isoformat(),
            reason=f"exceeded {result['max_age_hours']}h threshold (age: {result['staleness_hours']}h)",
        )


class QualityGate:
    """Validates observations before storage.

    Checks:
    1. Required fields (observation_id, source_id, observed_at, truth_class)
    2. Freshness via FreshnessChecker
    3. Returns a QualityAssessment
    """

    REQUIRED_FIELDS = {"observation_id", "source_id", "observed_at", "truth_class"}

    def __init__(self, registry: Optional[SourceRegistry] = None):
        self.freshness_checker = FreshnessChecker(registry)

    def validate(self, observation: dict[str, Any]) -> QualityAssessment:
        """Validate an observation dict before storage.

        Args:
            observation: dict with observation fields

        Returns:
            QualityAssessment with state and reason
        """
        now = datetime.now(timezone.utc)

        missing = self.REQUIRED_FIELDS - observation.keys()
        if missing:
            return QualityAssessment(
                state=QualityState.CONFLICTED,
                source_id=observation.get("source_id"),
                checked_at=now.isoformat(),
                reason=f"missing required fields: {', '.join(sorted(missing))}",
            )

        source_id = observation["source_id"]
        observed_at_str = observation.get("observed_at")

        last_observed = None
        if observed_at_str:
            try:
                last_observed = datetime.fromisoformat(observed_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return QualityAssessment(
                    state=QualityState.CONFLICTED,
                    source_id=source_id,
                    checked_at=now.isoformat(),
                    reason=f"invalid observed_at format: {observed_at_str}",
                )

        return self.freshness_checker.check(source_id, last_observed)

    def gate(self, observation: dict[str, Any]) -> tuple[bool, QualityAssessment]:
        """Run full quality gate — validate and check freshness.

        Args:
            observation: dict with observation fields

        Returns:
            Tuple of (passed, assessment). passed is True only if state is KNOWN or INFERRED.
        """
        assessment = self.validate(observation)
        passed = assessment.state in (QualityState.KNOWN, QualityState.INFERRED)
        return passed, assessment
