"""Puell-style miner-revenue transforms.

Puell = today's fresh issuance in USD divided by its own trailing mean.
>1 means miners are selling into a market paying them above trend,
<1 below trend. We publish the number and its percentile; we never publish a
directional label (agents.md: no bullish/bearish in output).

Everything here is computable from a daily price series plus a daily native
emission constant — both of which the warehouse already holds.
"""

from transforms.common import (
    MIN_PUELL_SAMPLES,
    daily_closes,
    percentile,
    refusal,
    result,
    rolling_mean,
)


def puell_series(price_rows, emission_per_day, window_days=365):
    """Daily issuance USD series and the trailing mean, from price alone."""
    closes = daily_closes(price_rows)
    issuance = [(date, close * emission_per_day) for date, close in closes]
    return closes, issuance


def puell_multiple(price_rows, emission_per_day, window_days=365, emission_source=None):
    """Puell Multiple for one chain. Refuses without `window_days` of data."""
    metric = "puell_multiple"
    closes, issuance = puell_series(price_rows, emission_per_day, window_days)
    if len(issuance) < MIN_PUELL_SAMPLES:
        return refusal(
            metric,
            "price history below minimum length",
            len(issuance),
            MIN_PUELL_SAMPLES,
        )
    if len(issuance) < window_days:
        return refusal(
            metric, "price history shorter than window", len(issuance), window_days
        )

    values = [value for _, value in issuance]
    mean = rolling_mean(values, window_days)
    if not mean:
        return refusal(metric, "trailing mean unavailable", len(values), window_days)
    today = values[-1]
    population = values[-window_days:]
    return result(
        metric,
        round(today / mean, 4),
        "x",
        len(values),
        emission_source or "price_history × daily native emission",
        window=f"{window_days}d",
        extra={
            "issuance_usd_day": round(today, 2),
            "issuance_usd_mean": round(mean, 2),
            "percentile_365d": percentile(today, population),
            "as_of": closes[-1][0],
        },
    )


def security_spend_ratio(
    price_rows, supply_rows, emission_per_day, window_days=365, emission_source=None
):
    """Emission USD as a share of market cap, using supply × price history."""
    metric = "security_spend_ratio"
    closes = dict(daily_closes(price_rows))
    supply = {}
    for row in supply_rows:
        date = row.get("event_time") or row.get("date")
        value = row.get("circulating_supply")
        if date and value:
            try:
                supply[str(date)[:10]] = float(value)
            except (TypeError, ValueError):
                continue
    joined = [
        (date, closes[date] * emission_per_day, closes[date] * supply[date])
        for date in sorted(closes)
        if supply.get(date)
    ]
    if len(joined) < MIN_PUELL_SAMPLES:
        return refusal(
            metric,
            "price and supply histories do not overlap enough",
            len(joined),
            MIN_PUELL_SAMPLES,
        )
    ratios = [(value / cap) for _, value, cap in joined if cap]
    if len(ratios) < window_days:
        return refusal(
            metric, "joined series shorter than window", len(ratios), window_days
        )
    mean = rolling_mean(ratios, window_days)
    if not mean:
        return refusal(metric, "trailing mean unavailable", len(ratios), window_days)
    return result(
        metric,
        round(ratios[-1] / mean, 4),
        "x",
        len(ratios),
        emission_source or "blockchain.info supply × price_history",
        window=f"{window_days}d",
        extra={
            "security_spend_usd_day": round(joined[-1][1], 2),
            "market_cap_usd": round(joined[-1][2], 2),
            "ratio_of_ratios_mean": round(mean, 4),
            "percentile_365d": percentile(ratios[-1], ratios[-window_days:]),
            "as_of": joined[-1][0],
        },
    )
