"""
Release + commit history collector — the event layer's memory.

Per tracked repo: releases (tag, name, published_at, body head) and
recent commits (sha, date, message head, files changed count). Stored
as protocol_event rows (releases) + repo_snapshot rows (commit stats).
Auto-classifies: CONSENSUS / TOKENOMICS / MINING / PERFORMANCE /
SECURITY / PRIVACY / MODEL / API from message+file signals.

Unauthenticated GitHub API (60 req/hr): ~15 repos x 2 calls = 30 calls
per pass. Weekly cadence is plenty; daily while young.

Usage:
    python3 scripts/collect_releases.py --once
"""

import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import fetch_json, store_normalized, utcnow  # noqa: E402

REPOS = {
    'PRL': 'pearl-research-labs/pearl',
    'QUBIC': 'qubic/core',
    'NOCK': 'nockchain/nockchain',
    'XMR': 'monero-project/monero',
    'KAS': 'kaspanet/rusty-kaspa',
    'XEL': 'xelis-project/xelis-blockchain',
    'QUAN': 'Quantus-Network/chain',
    'AKT': 'akash-network/node',
    'CLORE': None,  # no public repo tracked
    'NOS': None,
    'TAO': 'opentensor/bittensor',
    'FLUX': 'RunOnFlux/flux',
    'TSC': None,
    'GNK': 'gonka-ai/gonka',
    'XTM': 'tari-project/tari',
}

TAGS = {
    'CONSENSUS': ['consensus', 'fork', 'hardfork', 'softfork', 'chain split', 'reorg'],
    'TOKENOMICS': ['emission', 'reward', 'halving', 'supply', 'inflation', 'vesting', 'unlock'],
    'MINING': ['miner', 'mining', 'hashrate', 'pool', 'pow', 'difficulty', 'asic'],
    'PERFORMANCE': ['perf', 'optimiz', 'speed', 'throughput', 'latency', 'benchmark'],
    'SECURITY': ['security', 'vuln', 'cve', 'exploit', 'audit', 'attack'],
    'PRIVACY': ['privacy', 'ring', 'stealth', 'zk', 'zero-knowledge', 'shielded'],
    'MODEL': ['model', 'inference', 'llm', 'ai ', 'aigarth'],
    'API': ['api', 'rpc', 'endpoint', 'websocket'],
}


def classify(text):
    t = (text or '').lower()
    return [k for k, words in TAGS.items() if any(w in t for w in words)]


def collect_repo(sym, repo):
    base = f'https://api.github.com/repos/{repo}'
    rels = fetch_json(base + '/releases?per_page=20',
                      source_id='github-api', chain_id=sym.lower()) or []
    commits = fetch_json(base + '/commits?per_page=20',
                         source_id='github-api', chain_id=sym.lower()) or []
    n_rel = 0
    if isinstance(rels, list):
        for r in rels:
            body = f"{r.get('name', '')} {r.get('body', '')}"
            store_normalized('protocol_event', sym.lower(), {
                'symbol': sym, 'event_type': 'release',
                'tag': r.get('tag_name'), 'name': r.get('name'),
                'published_at': r.get('published_at'),
                'classes': classify(body),
                'source_role': 'derived', 'source_id': 'github-api'})
            n_rel += 1
    n_com = 0
    week_com = 0
    now = utcnow()
    if isinstance(commits, list):
        for c in commits:
            msg = (c.get('commit', {}) or {}).get('message', '')
            dt = ((c.get('commit', {}) or {}).get('author', {}) or {}).get('date', '')
            store_normalized('repo_commit', sym.lower(), {
                'symbol': sym, 'sha': c.get('sha'),
                'date': dt, 'message': msg[:300],
                'classes': classify(msg),
                'source_role': 'derived', 'source_id': 'github-api'})
            n_com += 1
    print(f"  [{sym}] releases={n_rel} commits_sampled={n_com}")
    time.sleep(2)  # unauthenticated rate limit courtesy
    return n_rel, n_com


def main():
    print(f"[RELEASES] {utcnow()}")
    tot = [0, 0]
    for sym, repo in REPOS.items():
        if not repo:
            print(f"  [{sym}] no tracked repo")
            continue
        try:
            a, b = collect_repo(sym, repo)
            tot[0] += a
            tot[1] += b
        except Exception as e:
            print(f"  [{sym}] ERR {str(e)[:120]}")
    print(f"[RELEASES] +{tot[0]} release events, +{tot[1]} commit rows")


if __name__ == '__main__':
    main()
