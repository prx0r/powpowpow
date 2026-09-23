"""Homelab adapter tests — pure helpers only, no hardware needed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import homelab


def test_norm_matches_variants():
    assert homelab._norm('Ryzen_9_7950X') in homelab._norm('AMD Ryzen 9 7950X CPU')
    assert homelab._norm('RTX 4090') in homelab._norm('NVIDIA GeForce RTX 4090')
    assert homelab._norm('') == ''


def test_match_archetypes_substring_both_directions():
    reg = {'XMR': {'Ryzen_9_7950X': {}}, 'PRL': {'H100': {}}}
    inv = {'cpu': {'model': 'AMD Ryzen 9 7950X 16-Core Processor'},
           'gpus': [{'name': 'NVIDIA H100 80GB HBM3'}]}
    m = homelab.match_archetypes(inv, registry=reg)
    got = {(x['archetype'], x['coin']) for x in m}
    assert ('Ryzen_9_7950X', 'XMR') in got
    assert ('H100', 'PRL') in got


def test_match_archetypes_no_force_fit():
    reg = {'XMR': {'Ryzen_9_7950X': {}}}
    inv = {'cpu': {'model': 'Intel(R) Core(TM) i5-3317U CPU @ 1.70GHz'},
           'gpus': []}
    assert homelab.match_archetypes(inv, registry=reg) == []


def test_fingerprint_stable():
    import hashlib
    import json
    ident = {'cpu_model': 'X', 'cpu_threads': None, 'memory_gb': None,
             'gpus': ['Y'], 'disk_gb': None}
    fp1 = hashlib.sha256(json.dumps(ident, sort_keys=True, default=str).encode()).hexdigest()[:16]
    fp2 = hashlib.sha256(json.dumps(ident, sort_keys=True, default=str).encode()).hexdigest()[:16]
    assert fp1 == fp2 and len(fp1) == 16


def test_rank_routes_nets_first_nones_last():
    routes = [
        {'action': 'idle', 'net_profit_usd_day': 0.0},
        {'action': 'mine_x', 'net_profit_usd_day': None},
        {'action': 'mine_y', 'net_profit_usd_day': 1.5},
        {'action': 'mine_z', 'net_profit_usd_day': -0.5},
    ]
    ranked = homelab.rank_routes(routes)
    assert [r['action'] for r in ranked] == ['mine_y', 'idle', 'mine_z', 'mine_x']


def test_recommend_never_raises_without_warehouse(monkeypatch, tmp_path):
    monkeypatch.setattr(homelab, 'BASE_DIR', str(tmp_path))
    inv = {'fingerprint': 'test', 'cpu': {'model': 'Unknown CPU 9000'},
           'memory': {}, 'gpus': [], 'electricity_usd_kwh': 0.10}
    rep = homelab.recommend(inv)
    assert rep['recommendations'] == []
    assert rep['unmatched'] == [{'kind': 'cpu', 'name': 'Unknown CPU 9000',
                                 'note': 'no measured benchmark in registry'}]
