"""
UKGraph Signal — the bridge between graph and content.

A Signal is a detected change or pattern in the economic graph
that is interesting enough to act on (route) or talk about (content).

From the architecture:
"Content is a deterministic view over graph signals."
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class SignalType(Enum):
    CHANGE = "CHANGE"           # What changed?
    WHY = "WHY"                 # Why is this changing?
    WHERE = "WHERE"             # Where is this strongest?
    COMPARE = "COMPARE"         # What beats what?
    OPPORTUNITY = "OPPORTUNITY" # What can someone do?
    WARNING = "WARNING"         # Who is exposed?


class ContentFrame(Enum):
    """How to frame this signal for content."""
    JOB_STRESS = "job_stress"
    RETRAINING = "retraining"
    OPPORTUNITY = "opportunity"
    GEOGRAPHIC = "geographic"
    COMPARISON = "comparison"
    WARNING = "warning"
    IGNORE = "ignore"


@dataclass
class Signal:
    """A detected change or pattern in the economic graph.
    
    Signals are the atomic unit of content generation.
    They flow: graph → signal detector → signal scorer → content compiler → video.
    """
    signal_id: str
    
    # What changed
    entity: str             # e.g. "graphic designers", "EV installation"
    place: str              # e.g. "UK", "Manchester", "OL1"
    metric: str             # e.g. "vacancy_rate", "median_pay", "business_formations"
    change: float           # magnitude of change (e.g. -0.27 = -27%)
    window: str             # e.g. "12m", "3m", "quarter"
    
    # Context
    related: dict = field(default_factory=dict)  # related signals
    evidence: list = field(default_factory=list)  # observation IDs
    confidence: float = 0.0
    
    # Content potential
    interestingness: float = 0.0
    content_frames: list = field(default_factory=list)  # suggested frames
    content_worthy: bool = False
    
    # Metadata
    source_garden: str = ""  # which garden detected this
    detected_at: str = ""    # ISO UTC
    expires_at: str = ""     # when this signal becomes stale
    
    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "entity": self.entity,
            "place": self.place,
            "metric": self.metric,
            "change": self.change,
            "window": self.window,
            "related": self.related,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "interestingness": self.interestingness,
            "content_frames": [f.value if hasattr(f, 'value') else f for f in self.content_frames],
            "content_worthy": self.content_worthy,
            "source_garden": self.source_garden,
            "detected_at": self.detected_at,
            "expires_at": self.expires_at,
        }


@dataclass
class ContentQuery:
    """A query for content generation based on a signal."""
    query_id: str
    signal_id: str
    frame: str  # CHANGE, WHY, WHERE, COMPARE, OPPORTUNITY, WARNING
    
    # What to expand
    seed_entity: str
    seed_metric: str
    seed_change: float
    
    # Expansion targets
    expand_metrics: list = field(default_factory=list)  # what other metrics to fetch
    expand_entities: list = field(default_factory=list)  # related entities
    expand_places: list = field(default_factory=list)    # geographic scope
    
    # Content constraints
    max_facts: int = 4
    tone: str = "informative"  # informative, urgent, encouraging, warning
    
    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "signal_id": self.signal_id,
            "frame": self.frame,
            "seed_entity": self.seed_entity,
            "seed_metric": self.seed_metric,
            "seed_change": self.seed_change,
            "expand_metrics": self.expand_metrics,
            "expand_entities": self.expand_entities,
            "expand_places": self.expand_places,
            "max_facts": self.max_facts,
            "tone": self.tone,
        }


@dataclass
class ContentManifest:
    """The output of content compilation — ready for rendering."""
    manifest_id: str
    signal_id: str
    query_id: str
    
    template: str        # which content template to use
    hook: str            # opening line
    claim: str           # the main claim
    proof: list = field(default_factory=list)  # supporting facts
    close: str = ""      # closing line / call to action
    
    source_ids: list = field(default_factory=list)  # evidence chain
    
    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "signal_id": self.signal_id,
            "query_id": self.query_id,
            "template": self.template,
            "hook": self.hook,
            "claim": self.claim,
            "proof": self.proof,
            "close": self.close,
            "source_ids": self.source_ids,
        }
