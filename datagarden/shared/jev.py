"""
Shared — Jev (TypeSafe System One) integration.

Cheap typed decisions for the data garden loop.

Usage:
    from shared.jev import classify_observation, score_hypothesis, classify_response

    result = classify_observation("Qubic difficulty rose 14% while price fell 3%")
    print(result["category"].choice)       # "difficulty_shift"
    print(result["severity"].score)        # 2.4
    print(result["actionable"].noul)       # 0.87
"""

import os
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

try:
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
    HAS_SDK = True
except ImportError:
    HAS_SDK = False

EXPERIMENTS_DIR = Path(__file__).parent.parent / 'experiments'


def _get_client():
    """Get TypeSafe client. Returns None if no API key."""
    if not HAS_SDK:
        return None
    api_key = os.environ.get('TYPESAFE_API_KEY')
    if not api_key:
        try:
            from agent_vault import get_key
            api_key = get_key('typesafe')
        except Exception:
            pass
    if not api_key:
        return None
    return TypeSafeClient()


def _save_result(tag: str, state: str, questions: dict, answers: dict):
    """Log Jev call to experiments/jev_log.jsonl."""
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = EXPERIMENTS_DIR / 'jev_log.jsonl'
    entry = {
        'timestamp': datetime.now().isoformat(),
        'tag': tag,
        'state_preview': state[:200],
        'answers': {},
    }
    for k, v in answers.items():
        if hasattr(v, 'choice'):
            entry['answers'][k] = {'choice': v.choice, 'confidence': getattr(v, 'confidence', None)}
        elif hasattr(v, 'score'):
            entry['answers'][k] = {'score': v.score, 'confidence': getattr(v, 'confidence', None)}
        elif hasattr(v, 'noul'):
            entry['answers'][k] = {'noul': v.noul}
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry, default=str) + '\n')


# ---------------------------------------------------------------------------
# FOREST: BREADUP — physical goods / used market
# ---------------------------------------------------------------------------

BREADUP_OBSERVATION_QUESTIONS = {
    "category": Choice(
        instructions="What type of market signal is this observation?",
        criteria={
            "price_drop": "Item or category prices declining",
            "price_spike": "Item or category prices increasing",
            "supply_glut": "Inventory or listing volume surging",
            "supply_squeeze": "Inventory drying up, items selling fast",
            "new_listing": "New product or SKU appeared on market",
            "discontinued": "Product discontinued or hard to find",
            "arbitrage": "Price gap between platforms or conditions",
            "condition_shift": "Average condition of sold items changing",
        },
    ),
    "severity": Score(
        instructions="How significant is this price movement for someone trying to flip this item?",
        criteria=["trivial", "minor", "moderate", "significant", "extreme"],
    ),
    "actionable": Noul(
        instructions="Could someone act on this signal today and make money?",
    ),
    "audience": Choice(
        instructions="Who would care most about this?",
        criteria={
            "reseller": "Buys and resells for profit",
            "hobbyist": "Consumer looking for deals",
            "collector": "Seeks rare or specific items",
            "trader": "Active in high-frequency buying/selling",
            "general": "Broad appeal, anyone interested in deals",
        },
    ),
}


# ---------------------------------------------------------------------------
# FOREST: ROOM / UKGraph — UK jobs & regulation
# ---------------------------------------------------------------------------

UKGRAPH_OBSERVATION_QUESTIONS = {
    "category": Choice(
        instructions="What type of UK economic signal is this?",
        criteria={
            "regulation": "New law, policy, or compliance requirement",
            "job_shift": "Employment rising or falling in a sector",
            "wage_signal": "Salary data changing meaningfully",
            "skill_gap": "Demand for workers outpacing supply",
            "crowding": "Too many people entering a field",
            "automation": "Technology replacing or augmenting jobs",
            "demographic": "Population or migration pattern shift",
            "infrastructure": "Physical investment or capacity change",
        },
    ),
    "urgency": Score(
        instructions="How time-sensitive is this for career decision-making?",
        criteria=["low", "moderate", "high", "critical"],
    ),
    "audience": Choice(
        instructions="Which audience segment should see this first?",
        criteria={
            "career_switcher": "Considering changing jobs or industries",
            "student": "Choosing education or first job",
            "tradesperson": "Electrician, plumber, builder, etc.",
            "professional": "Office/knowledge worker",
            "founder": "Business owner or startup founder",
            "investor": "Looking at economic trends",
        },
    ),
    "content_value": Noul(
        instructions="Is this signal specific enough and surprising enough to make a good 30-second video?",
    ),
}


# ---------------------------------------------------------------------------
# FOREST: POWPOWPROW — compute / mining economics
# ---------------------------------------------------------------------------

POWPOWPOW_OBSERVATION_QUESTIONS = {
    "category": Choice(
        instructions="What type of proof-of-work signal is this?",
        criteria={
            "difficulty_change": "Network difficulty adjusted",
            "price_move": "Coin price changed significantly",
            "hashrate_shift": "Hashrate rising or falling",
            "hardware_news": "New mining hardware or efficiency change",
            "energy_shift": "Electricity cost or availability changed",
            "pool_migration": "Miners moving between pools",
            "regulation": "Mining policy or legal change",
            "protocol_change": "Block reward, algorithm, or emission change",
        },
    ),
    "severity": Score(
        instructions="How much does this affect miner profitability right now?",
        criteria=["negligible", "minor", "moderate", "severe", "existential"],
    ),
    "actionable": Noul(
        instructions="Should a miner change their setup or strategy based on this?",
    ),
    "network": Choice(
        instructions="Which network does this primarily affect?",
        criteria={
            "bitcoin": "Bitcoin",
            "qubic": "Qubic",
            "monero": "Monero",
            "ethash": "Ethereum Classic or Ethash coins",
            "kawpow": "Ravennium or KawPow coins",
            "other": "Other proof-of-work network",
        },
    ),
}


# ---------------------------------------------------------------------------
# CONTENT PIPELINE — hypothesis scoring
# ---------------------------------------------------------------------------

HYPOTHESIS_SCORING_QUESTIONS = {
    "specific_audience": Noul(
        instructions="Does this title target a specific, identifiable group of people rather than everyone?",
    ),
    "novel_signal": Noul(
        instructions="Does this present information that is hard to find or not widely known?",
    ),
    "answerable_from_data": Noul(
        instructions="Can we actually support this claim with data we have collected or can collect?",
    ),
    "economic_consequence": Score(
        instructions="How directly does this affect someone's financial decisions?",
        criteria=["none", "entertaining", "interesting", "useful", "urgent"],
    ),
    "publish_candidate": Noul(
        instructions="Should we actually make a video about this? Consider: is it specific, true, surprising, and useful?",
    ),
}


# ---------------------------------------------------------------------------
# AUDIENCE RESPONSE — classify after publishing
# ---------------------------------------------------------------------------

AUDIENCE_RESPONSE_QUESTIONS = {
    "segment": Choice(
        instructions="Based on the comments and engagement, which audience segment responded strongest?",
        criteria={
            "reseller": "People interested in buying/selling for profit",
            "career_switcher": "People considering job changes",
            "hobbyist": "People doing it for personal interest",
            "investor": "People looking at trends to invest",
            "student": "People learning or choosing education",
            "general": "Broad, no specific segment dominates",
        },
    ),
    "sentiment": Choice(
        instructions="What is the dominant audience sentiment in comments?",
        criteria={
            "positive_engaged": "Actively interested, asking questions",
            "positive_casual": "Liked it but not deeply engaged",
            "mixed": "Some positive, some skeptical",
            "negative": "Mostly disagreement or criticism",
            "confused": "Audience didn't understand the point",
        },
    ),
    "repeatable": Noul(
        instructions="Does the engagement pattern suggest we should make more content like this?",
    ),
    "next_action": Choice(
        instructions="What should we do next based on this response?",
        criteria={
            "deepen": "Make a longer or more detailed follow-up",
            "pivot": "Try a different angle on the same topic",
            "series": "This is a recurring format, keep going",
            "prune": "The audience didn't care, move on",
            "explore": "This audience revealed an adjacent topic we should investigate",
        },
    ),
}


# ---------------------------------------------------------------------------
# PUBLIC API — thin wrappers
# ---------------------------------------------------------------------------

def _evaluate(tag: str, state: str, questions: dict) -> Optional[dict]:
    """Run a Jev evaluation. Returns answers dict or None."""
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.system_one(state=state, questions=questions)
        _save_result(tag, state, questions, response.answers)
        return response.answers
    except Exception as e:
        print(f"  Jev error ({tag}): {e}")
        return None


def classify_observation(state: str, forest: str = 'breadup') -> Optional[dict]:
    """Classify a raw observation from a forest.

    Args:
        state: Text description of the observation.
        forest: One of 'breadup', 'ukgraph', 'powpowpow'.

    Returns:
        Dict with typed answers, or None if Jev unavailable.
    """
    questions = {
        'breadup': BREADUP_OBSERVATION_QUESTIONS,
        'ukgraph': UKGRAPH_OBSERVATION_QUESTIONS,
        'powpowpow': POWPOWPOW_OBSERVATION_QUESTIONS,
    }.get(forest)
    if questions is None:
        return None
    return _evaluate(f'observe:{forest}', state, questions)


def score_hypothesis(state: str) -> Optional[dict]:
    """Score a content hypothesis before publishing.

    Args:
        state: Text describing the proposed content (title, angle, data).

    Returns:
        Dict with scoring answers, or None if Jev unavailable.
    """
    return _evaluate('hypothesis', state, HYPOTHESIS_SCORING_QUESTIONS)


def classify_response(state: str) -> Optional[dict]:
    """Classify audience response after publishing.

    Args:
        state: Comments, analytics summary, and context about the video.

    Returns:
        Dict with response classification, or None if Jev unavailable.
    """
    return _evaluate('response', state, AUDIENCE_RESPONSE_QUESTIONS)


def batch_classify(texts: list, forest: str = 'breadup') -> list:
    """Classify multiple observations in sequence.

    Args:
        texts: List of observation strings.
        forest: Which forest's question set to use.

    Returns:
        List of answer dicts (None for failures).
    """
    return [_evaluate(f'batch:{forest}:{i}', t, {
        'breadup': BREADUP_OBSERVATION_QUESTIONS,
        'ukgraph': UKGRAPH_OBSERVATION_QUESTIONS,
        'powpowpow': POWPOWPOW_OBSERVATION_QUESTIONS,
    }.get(forest, {})) for i, t in enumerate(texts)]


if __name__ == '__main__':
    # Quick test
    result = classify_observation(
        "Roland SP-404MKII median sold price dropped from £185 to £164 in 30 days. "
        "Listing volume up 22%. Condition mostly good. eBay UK.",
        forest='breadup',
    )
    if result:
        print(f"Category:   {result['category'].choice} (p={result['category'].probabilities})")
        print(f"Severity:   {result['severity'].score}")
        print(f"Actionable: {result['actionable'].noul}")
        print(f"Audience:   {result['audience'].choice}")
    else:
        print("Jev unavailable (set TYPESAFE_API_KEY)")
