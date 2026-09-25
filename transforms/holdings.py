"""Holdings transforms: exchange reserves and wealth concentration.

Feeds two questions nobody answers for QUBIC natively:
  1. how much of circulating supply sits on labelled exchange wallets,
  2. how concentrated is the rest.

Source of exchange labels is qubic/static `data/exchanges.json`, served at
static.qubic.org/v1/general/data/exchanges.json — a plain-name→identity map.
Balances come from `rpc.qubic.org/live/v1/balances/{id}`.

Pure functions, no I/O.
"""

from transforms.common import refusal, result

# Concentration thresholds reported for every snapshot.
TOP_FRACTIONS = (0.01, 0.10, 0.20, 0.50)


def gini(values):
    """Gini coefficient of a non-negative balance distribution."""
    clean = sorted(v for v in values if v is not None and v >= 0)
    if not clean:
        return None
    total = sum(clean)
    if total <= 0:
        return None
    n = len(clean)
    weighted = sum(value * index for index, value in enumerate(clean, start=1))
    return round((2 * weighted) / (n * total) - (n + 1) / n, 4)


def exchange_reserve(rows, circulating_supply=None, expected_entities=None):
    """Total QUs held by labelled exchange wallets, as share of supply."""
    metric = "exchange_reserve"
    usable = [row for row in rows if row.get("balance") is not None]
    if not usable:
        return refusal(metric, "no exchange balances fetched", 0, 1)
    try:
        amounts = [(row.get("name") or row.get("address") or "?", float(row["balance"]))
                   for row in usable]
    except (TypeError, ValueError):
        return refusal(metric, "malformed exchange balances", len(usable), 1)
    total = sum(amount for _, amount in amounts)
    breakdown = [
        {"name": name, "balance": round(amount, 0),
         "share": round(amount / total, 4) if total else None}
        for name, amount in sorted(amounts, key=lambda item: -item[1])
    ]
    complete = expected_entities is None or len(amounts) >= expected_entities
    extra = {
        "entities": len(amounts),
        "expected_entities": expected_entities,
        "partial": not complete,
        "missing_entities": (max(0, expected_entities - len(amounts))
                             if expected_entities else 0),
        "largest": breakdown[0]["name"] if breakdown else None,
        "largest_balance": breakdown[0]["balance"] if breakdown else None,
    }
    if circulating_supply and complete:
        extra["circulating_supply"] = round(circulating_supply, 0)
        extra["share_of_supply"] = round(total / circulating_supply, 6)
        extra["share_of_supply_pct"] = round(total / circulating_supply * 100, 3)
    extra["breakdown"] = breakdown
    return result(metric, round(total, 0), "QU", len(amounts),
                  "qubic/static exchanges.json + live/v1/balances",
                  window=("point in time" if complete
                          else "point in time — partial fetch"), extra=extra)


def wealth_concentration(balances, top_fractions=TOP_FRACTIONS, min_wallets=100):
    """Concentration of the rich list: gini plus top-fraction shares."""
    metric = "wealth_concentration"
    try:
        clean = sorted((float(v) for v in balances if v is not None),
                       reverse=True)
    except (TypeError, ValueError):
        clean = []
    if len(clean) < min_wallets:
        return refusal(metric, "rich list too small", len(clean), min_wallets)
    total = sum(clean)
    if total <= 0:
        return refusal(metric, "rich list has no positive balances",
                       len(clean), min_wallets)
    shares = {}
    for fraction in top_fractions:
        take = max(1, int(len(clean) * fraction))
        shares[f"top_{int(fraction * 100)}pct"] = round(
            sum(clean[:take]) / total, 4)
        shares[f"top_{int(fraction * 100)}pct_n"] = take
    mean = total / len(clean)
    median = clean[len(clean) // 2]
    return result(metric, gini(clean), "gini", len(clean),
                  "rpc.qubic.org/v1/rich-list",
                  window=f"top {len(clean)} holders",
                  extra={
                      "total_held": round(total, 0),
                      "mean_balance": round(mean, 0),
                      "median_balance": round(median, 0),
                      "mean_to_median": round(mean / median, 4) if median else None,
                      "shares": shares,
                  })


def exchange_share_of_top_holders(exchange_addresses, rich_entities):
    """What fraction of the richest N wallets are labelled exchanges."""
    metric = "exchange_share_of_top_holders"
    if not exchange_addresses:
        return refusal(metric, "no exchange address registry", 0, 1)
    if not rich_entities:
        return refusal(metric, "no rich list rows", 0, 1)
    labelled = {address.upper() for address in exchange_addresses}
    hits = [row for row in rich_entities
            if str(row.get("identity") or "").upper() in labelled]
    if not hits:
        return result(metric, 0.0, "share of rich list", 0,
                      "qubic/static exchanges.json ∩ rich-list",
                      window=f"top {len(rich_entities)}",
                      extra={"labelled_in_top": 0,
                             "rich_list_size": len(rich_entities)})
    held = sum(float(row.get("balance") or 0) for row in hits)
    total = sum(float(row.get("balance") or 0) for row in rich_entities)
    return result(metric, round(len(hits) / len(rich_entities), 4),
                  "share of rich list", len(rich_entities),
                  "qubic/static exchanges.json ∩ rich-list",
                  window=f"top {len(rich_entities)}",
                  extra={"labelled_in_top": len(hits),
                         "labelled_names": sorted({row.get("identity")
                                                   for row in hits})[:10],
                         "labelled_balance": round(held, 0),
                         "labelled_balance_share": round(held / total, 4)
                         if total else None})


def concentration_from_row(row, source=None):
    """Rebuild the concentration metric from a stored snapshot row."""
    metric = "wealth_concentration"
    if not row or row.get("gini") is None:
        return refusal(metric, "no wealth concentration snapshot stored", 0, 100)
    return result(
        metric, row.get("gini"), "gini", row.get("holders") or 0,
        source or "warehouse/normalized/qubic_wealth_concentration",
        window=f"top {row.get('holders')} holders",
        extra={
            "epoch": row.get("epoch"),
            "total_held": row.get("total_held"),
            "mean_balance": row.get("mean_balance"),
            "median_balance": row.get("median_balance"),
            "mean_to_median": row.get("mean_to_median"),
            "shares": row.get("shares"),
        },
    )


def exchange_share_from_row(row, source=None):
    """Rebuild the exchange-in-top-holders metric from a stored snapshot row."""
    metric = "exchange_share_of_top_holders"
    if not row:
        return refusal(metric, "no wealth concentration snapshot stored", 0, 1)
    return result(
        metric, row.get("exchange_share_of_top_holders"), "share of rich list",
        row.get("holders") or 0,
        source or "warehouse/normalized/qubic_wealth_concentration",
        window=f"top {row.get('holders')} holders",
        extra={
            "labelled_in_top": row.get("exchange_labelled_in_top"),
            "registry": "static.qubic.org/v1/general/data/exchanges.json",
        },
    )
