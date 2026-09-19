"""
PowPowPow — Content System Spec

The content loop is a sensor/actuator cycle on top of the dataset.
Each video is an experiment. YouTube analytics is the feedback signal.

Architecture:
  1. Event ingestion (GitHub, blogs, social)
  2. Anomaly detection (hard data)
  3. Story ranking (event + anomaly join)
  4. Content generation (script, charts, hypothesis)
  5. Outcome tracking (analytics, retention)
  6. Primitive learning (what works)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


# ============================================================
# EVENT LAYER — what happened in the world
# ============================================================

@dataclass
class ProjectEvent:
    """Normalized event from project feeds."""
    event_id: str
    network_id: str

    published_at: str
    observed_at: str

    source_type: str  # github_release, github_commit, blog, governance, exchange, social, protocol, research

    title: str
    body_summary: str
    source_url: str

    event_tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    numbers_extracted: List[Dict[str, Any]] = field(default_factory=list)

    importance_score: float = 0.0
    novelty_score: float = 0.0
    confidence: float = 0.5

    source_hash: Optional[str] = None


# ============================================================
# CONTENT EXPERIMENT — what we published and why
# ============================================================

@dataclass
class ContentSegment:
    """A segment within a video."""
    start_sec: int
    end_sec: int
    segment_type: str  # hook, setup, data, explanation, implication
    description: str
    primitives_used: List[str] = field(default_factory=list)
    chart_id: Optional[str] = None
    claim_ids: List[str] = field(default_factory=list)


@dataclass
class ContentExperiment:
    """A video is an experiment with hypotheses about what works."""
    video_id: str
    created_at: str
    published_at: Optional[str] = None

    # Source data
    source_events: List[str] = field(default_factory=list)  # event_ids
    source_metrics: List[Dict[str, Any]] = field(default_factory=list)

    # Content hypotheses
    thesis: str = ''
    hook: str = ''
    title_hypothesis: str = ''
    thumbnail_hypothesis: str = ''

    # Structure
    segments: List[ContentSegment] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    charts: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    # Metadata
    tone: str = ''  # analytical, dramatic, contrarian, educational
    complexity: float = 0.5  # 0=simple, 1=expert
    novelty_score: float = 0.0

    # Hypothesis
    predicted_ctr: Optional[float] = None
    predicted_30s_retention: Optional[float] = None
    predicted_rewatch_segments: List[str] = field(default_factory=list)


# ============================================================
# CONTENT OUTCOME — what actually happened
# ============================================================

@dataclass
class ContentOutcome:
    """YouTube analytics for a published experiment."""
    video_id: str
    measured_at: str

    # Top-level
    impressions: int = 0
    ctr: float = 0.0
    views: int = 0
    avg_view_duration_sec: float = 0.0
    avg_percentage_viewed: float = 0.0

    # Engagement
    likes: int = 0
    comments: int = 0
    shares: int = 0
    subs_gained: int = 0
    rewatches: int = 0

    # Retention curve (timestamp -> % retained)
    retention_curve: Dict[int, float] = field(default_factory=dict)

    # Traffic
    traffic_source: Optional[str] = None
    viewer_geography: Optional[Dict[str, float]] = None
    device: Optional[Dict[str, float]] = None


# ============================================================
# CONTENT PRIMITIVE — reusable building blocks
# ============================================================

@dataclass
class ContentPrimitive:
    """A reusable script/visual component with measured performance."""
    primitive_id: str
    primitive_type: str  # hook, visual, explanation

    description: str

    # Measured performance (updated as experiments accumulate)
    n_uses: int = 0
    mean_retention_uplift: float = 0.0
    mean_ctr_uplift: float = 0.0
    confidence: float = 0.0

    # Context dependence
    best_for_topics: List[str] = field(default_factory=list)
    worst_for_topics: List[str] = field(default_factory=list)


# ============================================================
# STORY RANKING — choosing what to cover
# ============================================================

CONTENT_VALUE_WEIGHTS = {
    'event_novelty': 0.20,
    'economic_magnitude': 0.25,
    'causal_clarity': 0.15,
    'historical_audience_interest': 0.20,
    'visualizability': 0.10,
    'timeliness': 0.10,
}


def score_story_candidate(
    event_novelty: float,
    economic_magnitude: float,
    causal_clarity: float,
    historical_audience_interest: float,
    visualizability: float,
    timeliness: float,
) -> float:
    """Score a story candidate for content value."""
    return (
        CONTENT_VALUE_WEIGHTS['event_novelty'] * event_novelty +
        CONTENT_VALUE_WEIGHTS['economic_magnitude'] * economic_magnitude +
        CONTENT_VALUE_WEIGHTS['causal_clarity'] * causal_clarity +
        CONTENT_VALUE_WEIGHTS['historical_audience_interest'] * historical_audience_interest +
        CONTENT_VALUE_WEIGHTS['visualizability'] * visualizability +
        CONTENT_VALUE_WEIGHTS['timeliness'] * timeliness
    )


# ============================================================
# DAILY PROCESS
# ============================================================

DAILY_CONTENT_PIPELINE = """
1. INGEST
   - Fetch project events (GitHub, blogs, social)
   - Fetch latest market/resource anomalies from warehouse
   - Fetch previous video outcomes

2. DETECT
   - Join events with hard-data anomalies
   - Identify causal explanations (event X may explain anomaly Y)
   - Score novelty, magnitude, clarity

3. RANK
   - Score each candidate story
   - Check historical audience interest for similar topics
   - Apply exploration bonus (contextual bandit)

4. GENERATE
   - Choose story
   - Select proven/experimental primitives for hook, visual, explanation
   - Generate charts from warehouse data
   - Write script as hypothesis

5. PUBLISH
   - Upload video
   - Record content_experiment

6. MEASURE
   - After 24h/7d/30d: fetch content_outcome
   - Compute segment-level retention
   - Compare against hypothesis

7. LEARN
   - Update primitive performance stats
   - Update topic interest priors
   - Update content model weights
"""


# ============================================================
# CONTENT PRIMITIVES — canonical set
# ============================================================

CANONICAL_PRIMITIVES = [
    # Hooks
    ContentPrimitive('HOOK_SCARCITY', 'hook', 'Frame around physical scarcity or stockout'),
    ContentPrimitive('HOOK_SURPRISE', 'hook', 'Present unexpected data or counterintuitive finding'),
    ContentPrimitive('HOOK_DOLLAR_VALUE', 'hook', 'Lead with specific dollar amount or percentage'),
    ContentPrimitive('HOOK_CONTRARIAN', 'hook', 'Challenge common narrative with data'),

    # Visuals
    ContentPrimitive('VISUAL_SEESAW', 'visual', 'Two-sided chart showing supply/demand balance'),
    ContentPrimitive('VISUAL_RESOURCE_FLOW', 'visual', 'Animate hardware moving between markets'),
    ContentPrimitive('VISUAL_MINER_MARGIN', 'visual', 'Show miner profitability vs external rent'),
    ContentPrimitive('VISUAL_SUPPLY_CURVE', 'visual', 'Plot supply response over time'),

    # Explanations
    ContentPrimitive('EXPLANATION_ANALOGY', 'explanation', 'Map to familiar real-world analogy'),
    ContentPrimitive('EXPLANATION_CAUSAL_CHAIN', 'explanation', 'Step-by-step causal sequence'),
    ContentPrimitive('EXPLANATION_COUNTERFACTUAL', 'explanation', 'What would have happened otherwise'),
]
