from pathlib import Path

from scripts import btc_mining_backtest
from scripts import qubic_analytics
from scripts import qubic_epoch
import coins
import v1_live_cards


def test_broken_legacy_mining_scripts_are_quarantined():
    root = Path(__file__).resolve().parents[1]
    names = (
        "collect_mining.py",
        "collect_miner_revenue.py",
        "collect_chain_stats.py",
        "collect_github.py",
    )
    for name in names:
        assert not (root / "scripts" / name).exists()
        assert (root / "legacy" / "mining-2026-09-25" / name).exists()


def test_xmr_tail_emission_constants():
    assert coins.get_coin("XMR")["chain"]["emission_per_day"] == 432
    assert v1_live_cards.NETWORK["XMR"]["daily_emission"] == 432.0
    assert 0.6 * 720 == 432


def test_btc_post_halving_emission_constant():
    assert 3.125 * 144 == 450.0


def test_qubic_post_227_burn_and_effective_emission():
    assert qubic_epoch.burn_rate_for_epoch(232) == 0.775
    assert qubic_epoch.POST_227_MAX_NET_PER_WEEK == 225e9
    assert qubic_epoch.POST_227_MAX_NET_PER_WEEK / 7 == 32142857142.857143


def test_qubic_reward_uses_minimum_mineable_supply():
    economics = qubic_analytics.computor_economics(
        {"burn_rate": 0.775, "computors": 676}
    )
    assert economics["effective_per_epoch"] == 225e9
    assert economics["mineable_per_epoch"] == 181.64e9
    assert economics["reward_per_computor"] == 181.64e9 / 676


def test_qubic_supply_curve_projects_new_issuance():
    curve = qubic_analytics.supply_curve({"burn_rate": 0.775})
    assert curve[0]["new_supply"] == 225e9
    assert curve[0]["net"] == 225e9
    assert curve[1]["new_supply"] == 450e9


def test_btc_hashprice_uses_petahashes():
    assert btc_mining_backtest.hashprice_ph_day(100.0, 1e9) == 0.1
    assert btc_mining_backtest.hashrate_ghs(
        {"network_hashrate_ghs": 1e9, "network_hashrate_ths": 2e9}
    ) == 1e9
    assert btc_mining_backtest.hashrate_ghs({"network_hashrate_ths": 2e9}) == 2e9


def test_network_share_revenue_formula():
    assert v1_live_cards.mining_revenue_usd_day(1.0, 10.0, 100.0, 2.0) == 20.0
    assert v1_live_cards.mining_revenue_usd_day(None, 10.0, 100.0, 2.0) is None
    assert v1_live_cards.mining_revenue_usd_day(1.0, 0.0, 100.0, 2.0) is None
