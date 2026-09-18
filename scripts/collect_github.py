"""
GitHub Stats Collector for PowPowPow
Fetches repo activity, commits, releases, and developer metrics.
"""

import json
import os
import requests
from datetime import datetime, timedelta

DATA_DIR = '/home/box/powpowpow/chains'
os.makedirs(DATA_DIR, exist_ok=True)

# All repos to track
REPOS = {
    'QUBIC': ['qubic/core', 'qubic/go-qubic-nodes', 'qubic/qct', 'qubic/docs', 'qubic/oracle-machine'],
    'PRL': ['pearl-research-labs/pearl'],
    'NOCK': ['nockchain/nockchain'],
    'XMR': ['monero-project/monero', 'monero-project/monero-gui'],
    'GNK': ['gonka-ai/gonka', 'gonka-ai/gonka-openai'],
    'TSC': ['tensorcash/tensorcash'],
    'XEL': ['xelis-project/xelis-blockchain', 'xelis-project/xelis-hash'],
    'XTM': ['tari-project/tari', 'tari-project/tari-crypto', 'tari-project/universe'],
    'NPT': [],
    'QTC': [],
}

def fetch_repo_stats(repo):
    """Fetch stats for a single GitHub repo."""
    try:
        url = f'https://api.github.com/repos/{repo}'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'name': data.get('full_name'),
                'description': data.get('description'),
                'stars': data.get('stargazers_count'),
                'forks': data.get('forks_count'),
                'open_issues': data.get('open_issues_count'),
                'watchers': data.get('subscribers_count'),
                'language': data.get('language'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'pushed_at': data.get('pushed_at'),
                'size_kb': data.get('size'),
                'default_branch': data.get('default_branch'),
                'topics': data.get('topics', []),
                'license': data.get('license', {}).get('spdx_id') if data.get('license') else None,
            }
    except Exception as e:
        print(f"    Error fetching {repo}: {e}")
    return None

def fetch_recent_commits(repo, days=7):
    """Fetch recent commit count."""
    try:
        url = f'https://api.github.com/repos/{repo}/commits'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        since = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
        params = {'since': since, 'per_page': 100}
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            commits = resp.json()
            return {
                'count_7d': len(commits),
                'authors': list(set(c.get('commit', {}).get('author', {}).get('name', '') for c in commits)),
            }
    except Exception as e:
        pass
    return {'count_7d': 0, 'authors': []}

def fetch_releases(repo, limit=3):
    """Fetch recent releases."""
    try:
        url = f'https://api.github.com/repos/{repo}/releases'
        headers = {'Accept': 'application/vnd.github.v3+json'}
        params = {'per_page': limit}
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            releases = resp.json()
            return [{
                'tag': r.get('tag_name'),
                'name': r.get('name'),
                'published_at': r.get('published_at'),
                'prerelease': r.get('prerelease'),
            } for r in releases[:limit]]
    except Exception as e:
        pass
    return []

def collect_github_stats():
    """Collect GitHub stats for all tracked coins."""
    print(f"\n{'='*60}")
    print(f"Collecting GitHub Stats — {datetime.now()}")
    print(f"{'='*60}")
    
    all_stats = {}
    
    for coin, repos in REPOS.items():
        if not repos:
            print(f"\n[{coin}] No GitHub repos tracked")
            continue
        
        print(f"\n[{coin}]")
        coin_stats = {
            'coin': coin,
            'repos': [],
            'total_stars': 0,
            'total_forks': 0,
            'total_commits_7d': 0,
            'active_developers': set(),
        }
        
        for repo in repos:
            print(f"  [{repo}]")
            
            stats = fetch_repo_stats(repo)
            if stats:
                commits = fetch_recent_commits(repo)
                releases = fetch_releases(repo)
                
                repo_data = {
                    **stats,
                    'commits_7d': commits.get('count_7d', 0),
                    'recent_releases': releases,
                }
                coin_stats['repos'].append(repo_data)
                coin_stats['total_stars'] += stats.get('stars', 0) or 0
                coin_stats['total_forks'] += stats.get('forks', 0) or 0
                coin_stats['total_commits_7d'] += commits.get('count_7d', 0)
                coin_stats['active_developers'].update(commits.get('authors', []))
                
                print(f"    Stars: {stats.get('stars', 0)} | Forks: {stats.get('forks', 0)} | Commits 7d: {commits.get('count_7d', 0)}")
            else:
                print(f"    No data")
        
        # Convert set to count
        coin_stats['active_developers'] = len(coin_stats['active_developers'])
        all_stats[coin] = coin_stats
        
        print(f"  Total: {coin_stats['total_stars']} stars, {coin_stats['total_forks']} forks, {coin_stats['total_commits_7d']} commits/7d, {coin_stats['active_developers']} devs")
    
    # Save
    output = {}
    for coin, stats in all_stats.items():
        stats['collected_at'] = datetime.now().isoformat()
        output[coin] = stats
    
    output_file = os.path.join(DATA_DIR, 'github_stats.json')
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[SAVED] {output_file}")
    
    return all_stats

if __name__ == '__main__':
    collect_github_stats()
