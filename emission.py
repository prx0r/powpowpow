"""
Emission schedules — researched daily native emission per asset.

Each entry carries formula/params + source + confidence + as_of. Live
measurement (supply-delta collectors) overrides these seeds wherever
available; signals.py prefers measured values and cites whichever won.
"""

from datetime import datetime, timezone

SCHEDULES = {
    # CLORE: ERC-20 rewards pool. 164k/day initial, -30%/yr, monthly
    # factor 0.7**(1/12). Start assumed at L1-claim era mid-2025.
    'CLORE': {'kind': 'decay', 'base_per_day': 164000.0,
              'annual_factor': 0.7, 'start': '2025-06-01',
              'source': 'docs.clore.ai/tokenomics (164k/d initial, -30%/yr)',
              'confidence': 'low', 'as_of': '2026-09-19'},
    # FLUX: ~7.0 FLUX/block (minerstat Aug 2026), 30s blocks = 2880/d,
    # 10%/yr decay toward 560M max.
    'FLUX': {'kind': 'per_block', 'per_block': 7.0, 'blocks_per_day': 2880,
             'annual_factor': 0.9, 'start': '2026-08-01',
             'source': 'minerstat block reward 7.0 + 30s blocks + 10%/yr program',
             'confidence': 'medium-low', 'as_of': '2026-09-19'},
    # NOS: vesting math. Team 20M/48mo + company 25M/36mo linear from
    # ~2024-01 TGE (mining 20M/24mo likely expired). ~36.5k/d while
    # windows active. NNP-0001 sunsetting passive staking separately.
    'NOS': {'kind': 'flat', 'per_day': 36500.0,
            'source': 'learn.nosana.com token pools (team 20M/48mo + company 25M/36mo)',
            'confidence': 'low', 'as_of': '2026-09-19'},
    # TAO: 0.5/block post-Dec-2025 halving, ~3600/d. Context only
    # (Bittensor-native territory per focus rule).
    'TAO': {'kind': 'flat', 'per_day': 3600.0,
            'source': 'bittensor docs/emissions (0.5 TAO/block)',
            'confidence': 'medium', 'as_of': '2026-09-19'},
    # NOCK: 50k/d from fundamentals (single source, unverified schedule).
    'NOCK': {'kind': 'flat', 'per_day': 50000.0,
             'source': 'chain_fundamentals.json (schedule unverified)',
             'confidence': 'low', 'as_of': '2026-09-19'},
}


def estimate(symbol, at=None):
    """Return (per_day, provenance_dict) or (None, {}) if unknown."""
    s = SCHEDULES.get(symbol.upper())
    if not s:
        return None, {}
    at = at or datetime.now(timezone.utc).date().isoformat()
    try:
        if s['kind'] == 'flat':
            return float(s['per_day']), s
        if s['kind'] == 'per_block':
            years = (datetime.fromisoformat(at).date() -
                     datetime.fromisoformat(s['start']).date()).days / 365.25
            decay = s.get('annual_factor', 1.0) ** max(0.0, years)
            return float(s['per_block'] * s['blocks_per_day'] * decay), s
        if s['kind'] == 'decay':
            years = (datetime.fromisoformat(at).date() -
                     datetime.fromisoformat(s['start']).date()).days / 365.25
            return float(s['base_per_day'] * (s['annual_factor'] ** max(0.0, years))), s
    except (ValueError, KeyError, TypeError):
        pass
    return None, {}
