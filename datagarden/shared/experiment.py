"""
Shared — PublicationExperiment

Every tree logs the same experiment structure.
This is the contract between data, content, and analytics.
"""

import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class PublicationExperiment:
    """One experiment = one video published from one tree."""

    # Identity
    experiment_id: str
    forest: str          # breadup, room, me, powpowpow
    tree: str            # job_demand, used_market_pressure, resource_flow
    audience: str        # who we think will watch

    # Hypothesis
    title: str
    title_hypothesis: str   # why we think this hits
    answer_metric: str      # what we measured
    answer_value: float     # the actual number
    confidence: float       # 0-1, how sure are we
    evidence: List[str]     # supporting data points

    # Publication
    video_id: Optional[str] = None
    published_at: Optional[str] = None
    platform: str = 'youtube_shorts'

    # Outcome (filled after publishing)
    impressions: Optional[int] = None
    ctr: Optional[float] = None
    views: Optional[int] = None
    avg_view_duration: Optional[float] = None
    avg_view_percentage: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    subs_gained: Optional[int] = None

    # Decision
    decision: Optional[str] = None  # prune / continue / deepen
    next_hypothesis: Optional[str] = None

    # Metadata
    created_at: str = ''
    data_source: str = ''
    data_collected_at: str = ''

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def record_outcome(self, impressions=None, ctr=None, views=None,
                       avg_view_duration=None, avg_view_percentage=None,
                       likes=None, comments=None, shares=None, subs_gained=None):
        """Record YouTube analytics after publishing."""
        if impressions is not None: self.impressions = impressions
        if ctr is not None: self.ctr = ctr
        if views is not None: self.views = views
        if avg_view_duration is not None: self.avg_view_duration = avg_view_duration
        if avg_view_percentage is not None: self.avg_view_percentage = avg_view_percentage
        if likes is not None: self.likes = likes
        if comments is not None: self.comments = comments
        if shares is not None: self.shares = shares
        if subs_gained is not None: self.subs_gained = subs_gained

    def decide(self, threshold_ctr: float = 0.05, threshold_retention: float = 0.5):
        """Auto-decide based on analytics."""
        if self.ctr is None:
            self.decision = 'pending'
            return

        if self.ctr >= threshold_ctr and (self.avg_view_percentage or 0) >= threshold_retention:
            self.decision = 'deepen'
        elif self.ctr >= threshold_ctr * 0.5:
            self.decision = 'continue'
        else:
            self.decision = 'prune'

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, filepath: str):
        """Save experiment to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> 'PublicationExperiment':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


EXPERIMENT_TEMPLATE = {
    "experiment_id": "",
    "forest": "",
    "tree": "",
    "audience": "",
    "title": "",
    "title_hypothesis": "",
    "answer_metric": "",
    "answer_value": 0,
    "confidence": 0.0,
    "evidence": [],
    "video_id": None,
    "published_at": None,
    "platform": "youtube_shorts",
    "impressions": None,
    "ctr": None,
    "views": None,
    "avg_view_duration": None,
    "avg_view_percentage": None,
    "likes": None,
    "comments": None,
    "shares": None,
    "subs_gained": None,
    "decision": None,
    "next_hypothesis": None,
    "created_at": "",
    "data_source": "",
    "data_collected_at": "",
}


if __name__ == '__main__':
    # Example experiment
    exp = PublicationExperiment(
        experiment_id='breadup-mispricing-001',
        forest='breadup',
        tree='used_market_pressure',
        audience='resellers, side-hustlers',
        title='The used synths getting cheaper fastest',
        title_hypothesis='People want arbitrage opportunities. Price drops are actionable.',
        answer_metric='price_change_30d',
        answer_value=-11.4,
        confidence=0.85,
        evidence=['Roland SP-404MKII median ask down 11.4% in 30d', 'Inventory up 22%'],
        data_source='ebay_uk_sold',
        data_collected_at='2026-09-19',
    )
    print(json.dumps(exp.to_dict(), indent=2))
