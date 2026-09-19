"""
Live Card Builder (compat shim).

Delegates to v1_live_cards (network-share model). Kept so old imports
(`from live_cards import build_card`) keep working without divergence.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from v1_live_cards import generate_card, print_card, generate_all_cards  # noqa: F401


def build_card(coin, price, hashrate=None, difficulty=None, emission=None,
               network_data=None, electricity=0.10):
    """Legacy signature — hashrate/difficulty/emission args ignored in favor
    of registry network state; network_data overrides when supplied."""
    return generate_card(coin, price, network_data=network_data, electricity=electricity)


def build_all_cards(electricity=0.10):
    return generate_all_cards(electricity=electricity)


if __name__ == '__main__':
    generate_all_cards()
