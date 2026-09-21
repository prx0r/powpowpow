import os
"""
PowPowPow Tier 1 Categories
Hard mining/hardware assets only.
"""

CATEGORIES = {
    'useful-pow': {
        'name': 'Useful Proof-of-Work',
        'description': 'Mining produces useful computation',
        'scarce_resource': 'Compute / Proof / Useful Work',
        'coins': ['QUBIC', 'PRL', 'TSC', 'GNK', 'TIG'],
    },
    'pow-privacy': {
        'name': 'PoW / Privacy / Security',
        'description': 'Mining for security/privacy',
        'scarce_resource': 'Consensus security / Privacy',
        'coins': ['XMR', 'QUAN', 'QRL', 'MCM'],
    },
}

COIN_CATEGORIES = {}
for cat_id, cat in CATEGORIES.items():
    for coin in cat['coins']:
        if coin not in COIN_CATEGORIES:
            COIN_CATEGORIES[coin] = []
        COIN_CATEGORIES[coin].append(cat_id)
