"""Build insight metrics from warehouse history and join them to price.

Pure transforms live in transforms/; this module only reads the warehouse and
writes one snapshot: warehouse/insights.json. Refusals are kept in the payload
so a missing metric is visibly missing, never absent and unexplained.

Usage:
    python3 scripts/build_insights.py
    python3 scripts/build_insights.py --date 2026-09-25
"""

import argparse
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core import utcnow
from transforms import (
    TRANSFORM_VERSION,
    active_address_growth,
    activity_metrics,
    burn_intensity,
    burn_profile,
    concentration_from_row,
    daily_closes,
    exchange_reserve,
    exchange_share_from_row,
    intraday_price_correlation,
    metric_vs_price_corr,
    percentile,
    price_hashrate_divergence,
    puell_multiple,
    security_spend_ratio,
    tick_quality_ribbon,
)

OUTPUT_FILE = os.path.join(BASE_DIR, "warehouse", "insights.json")

CHAINS = ("BTC", "XMR", "QUBIC")

# Chain -> emission source order used by signals.load_emission.
try:
    from signals import load_emission
except (ImportError, AttributeError):
    load_emission = None


def read_table(table, chain):
    rows = []
    pattern = os.path.join(
        BASE_DIR,
        "warehouse",
        "normalized",
        table,
        f"chain={chain}",
        "date=*",
        "hour=*.jsonl",
    )
    for path in glob.glob(pattern):
        try:
            with open(path) as handle:
                for line in handle:
                    if line.strip():
                        rows.append(json.loads(line))
        except (OSError, ValueError):
            continue
    return rows


def price_context(closes):
    if not closes:
        return None, None, None
    values = [value for _, value in closes]
    window = values[-365:] if len(values) >= 365 else values
    return values[-1], percentile(values[-1], window), closes[-1][0]


def _exchange_registry():
    """Cached exchange registry size, for completeness checks."""
    path = os.path.join(BASE_DIR, "warehouse", "knowledge", "qubic_exchanges.json")
    try:
        with open(path) as handle:
            return json.load(handle).get("exchanges") or []
    except (OSError, ValueError):
        return []


def qubic_holdings_metrics(stats_rows):
    """Exchange reserves and wealth concentration, from stored snapshots."""
    supply = None
    if stats_rows:
        rows = sorted(stats_rows, key=lambda row: row.get("observed_at") or "")
        supply = rows[-1].get("circulating_supply")
    supply = int(supply) if supply else None

    balances = read_table("qubic_exchange_balance", "qubic")
    latest = {}
    for row in balances:
        if row.get("address"):
            latest[row["address"]] = row
    if not latest:
        return [{
            "metric": "exchange_reserve", "refused": True,
            "reason": "no exchange balances collected yet", "n": 0,
            "version": TRANSFORM_VERSION,
        }]

    expected = len(_exchange_registry())
    out = [exchange_reserve(list(latest.values()),
                            circulating_supply=supply,
                            expected_entities=expected or None)]
    concentration = read_table("qubic_wealth_concentration", "qubic")
    concentration.sort(key=lambda row: row.get("observed_at") or "")
    snapshot = concentration[-1] if concentration else None
    out.append(concentration_from_row(snapshot))
    out.append(exchange_share_from_row(snapshot))
    return out


def build(root=BASE_DIR):
    price_rows = {chain: read_table("price_history", chain.lower()) for chain in CHAINS}
    stats_rows = read_table("qubic_stats", "qubic")

    chains = {}
    for chain in CHAINS:
        closes = daily_closes(price_rows[chain])
        price, price_pct, as_of = price_context(closes)

        emission, emission_source = (None, None)
        if load_emission:
            try:
                emission, emission_source = load_emission(chain)
            except (OSError, ValueError, TypeError, KeyError):
                emission, emission_source = (None, None)

        metrics = []

        if emission and closes:
            metrics.append(
                puell_multiple(
                    price_rows[chain],
                    emission,
                    window_days=365,
                    emission_source=f"{emission_source} × price_history",
                )
            )
        else:
            metrics.append(
                {
                    "metric": "puell_multiple",
                    "refused": True,
                    "reason": "no daily emission for chain",
                    "n": 0,
                    "version": TRANSFORM_VERSION,
                }
            )

        if chain == "BTC":
            supply_rows = [
                row
                for row in read_table("chain_snapshot", "btc")
                if row.get("circulating_supply")
            ]
            if emission:
                metrics.append(
                    security_spend_ratio(
                        price_rows[chain],
                        supply_rows,
                        emission,
                        window_days=365,
                        emission_source="blockchain.info supply × price_history",
                    )
                )
            hashrate_rows = [
                row
                for row in read_table("chain_snapshot", "btc")
                if row.get("network_hashrate_ths")
            ]
            metrics.append(
                price_hashrate_divergence(
                    price_rows[chain],
                    hashrate_rows,
                    window=30,
                    field_note="price_history vs network_hashrate_ths",
                )
            )
        elif chain == "XMR":
            hashrate_rows = [
                row
                for row in read_table("chain_snapshot", "xmr")
                if row.get("network_hashrate")
            ]
            metrics.append(
                price_hashrate_divergence(
                    price_rows[chain],
                    hashrate_rows,
                    window=10,
                    field_note="price_history vs network_hashrate (~3d grain)",
                )
            )
        else:
            metrics.append(
                price_hashrate_divergence(
                    price_rows[chain],
                    [],
                    window=30,
                    field_note="no hashrate history collected for QUBIC",
                )
            )

        if chain == "QUBIC":
            netstate = {}
            try:
                with open(
                    os.path.join(BASE_DIR, "chains", "network_state.json")
                ) as handle:
                    netstate = json.load(handle).get("QUBIC", {})
            except (OSError, ValueError):
                netstate = {}
            epochs = read_table("qubic_epoch", "qubic")
            epochs.sort(key=lambda row: row.get("observed_at") or "")
            initial_tick = epochs[-1].get("initial_tick") if epochs else None
            gross = netstate.get("gross_per_week")
            burn_rate = netstate.get("burn_rate")
            scheduled = (gross * burn_rate) if gross and burn_rate else None

            metrics.extend(
                [
                    tick_quality_ribbon(stats_rows),
                    active_address_growth(stats_rows),
                ]
            )
            metrics.extend(
                burn_profile(
                    read_table("qubic_burn_event", "qubic"),
                    initial_tick=initial_tick,
                    scheduled_burn=scheduled,
                )
            )
            metrics.append(burn_intensity(stats_rows))
            transfer_rows = read_table("qubic_transfer_window", "qubic")
            metrics.extend(activity_metrics(transfer_rows))
            # SafeTrade depth deltas often carry one side only, so `mid` is
            # sparse (489 of 16,810 rows). The ticker table has a complete
            # `last` for the same market and is the better intraday price.
            qubic_mids = [
                {"observed_at": row.get("observed_at") or row.get("receive_time"),
                 "mid": row.get("last")}
                for row in read_table("ticker", "safetrade")
                if (row.get("symbol") or "").lower() == "qubicusdt"
                and row.get("last") not in (None, 0)
            ]
            metrics.append(intraday_price_correlation(transfer_rows, qubic_mids))
            metrics.extend(qubic_holdings_metrics(stats_rows))
            for name, field in (("epoch_tick_quality", "epoch_tick_quality"),):
                metrics.append(
                    metric_vs_price_corr(
                        [
                            (row.get("observed_at") or "", row.get(field))
                            for row in stats_rows
                            if row.get(field) is not None
                        ],
                        price_rows[chain],
                        window=30,
                        metric_name=name,
                    )
                )

        chains[chain] = {
            "price_usd": price,
            "price_percentile_365d": price_pct,
            "price_as_of": as_of,
            "daily_emission": emission,
            "emission_source": emission_source,
            "metrics": metrics,
        }

    computed = sum(
        1
        for chain in chains.values()
        for metric in chain["metrics"]
        if not metric.get("refused")
    )
    refused = sum(
        1
        for chain in chains.values()
        for metric in chain["metrics"]
        if metric.get("refused")
    )
    payload = {
        "generated_at": utcnow(),
        "version": TRANSFORM_VERSION,
        "chains": chains,
        "summary": {
            "metrics": computed + refused,
            "computed": computed,
            "refused": refused,
        },
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    temporary = OUTPUT_FILE + ".tmp"
    with open(temporary, "w") as handle:
        json.dump(payload, handle, indent=2, default=str)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, OUTPUT_FILE)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="accepted for scheduling symmetry")
    ap.parse_args()
    payload = build()
    summary = payload["summary"]
    print(
        f"[INSIGHTS] {summary['computed']} computed, "
        f"{summary['refused']} refused -> {OUTPUT_FILE}"
    )
    for chain, block in payload["chains"].items():
        print(
            f"  {chain:6} price={block['price_usd']} "
            f"pctl365={block['price_percentile_365d']}"
        )
        for metric in block["metrics"]:
            if metric.get("refused"):
                print(
                    f"      {metric['metric']:32} REFUSED "
                    f"({metric.get('reason')}, n={metric.get('n')}, "
                    f"min={metric.get('min_n')})"
                )
            else:
                print(
                    f"      {metric['metric']:32} {metric['value']} "
                    f"{metric['unit']} (n={metric['n']})"
                )


if __name__ == "__main__":
    main()
