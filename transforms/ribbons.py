"""Ribbon, divergence and burn-intensity transforms.

These are the QUBIC-native metric families (tick quality, active addresses,
burns) plus price-divergence composites. Each refuses with a reason rather than
emitting a thin number.

Positional wording only — "above/below mean" describes a measurement, not a
directional opinion. No bullish/bearish/buy/sell anywhere in this module.
"""

from transforms.common import (
    MIN_CORR_SAMPLES,
    MIN_RIBBON_SAMPLES,
    align,
    pct_change,
    pearson,
    percentile,
    refusal,
    result,
    rolling_mean,
    zscore,
)


def _stats_series(rows, field):
    ordered = []
    for row in rows:
        value = row.get(field)
        stamp = row.get("observed_at") or row.get("timestamp")
        if value is None or not stamp:
            continue
        try:
            ordered.append((stamp, float(value)))
        except (TypeError, ValueError):
            continue
    ordered.sort(key=lambda item: item[0])
    return ordered


def tick_quality_ribbon(
    stats_rows, field="last10000_tick_quality", window=MIN_RIBBON_SAMPLES
):
    """Tick-quality level vs its own trailing mean, with cross count."""
    metric = "tick_quality_ribbon"
    series = _stats_series(stats_rows, field)
    if len(series) < window:
        return refusal(
            metric, "not enough tick-quality snapshots yet", len(series), window
        )
    values = [value for _, value in series]
    mean = rolling_mean(values, window)
    if mean is None:
        return refusal(metric, "trailing mean unavailable", len(values), window)

    crosses = 0
    for index in range(1, len(values)):
        if (values[index - 1] - mean) * (values[index] - mean) < 0:
            crosses += 1
    return result(
        metric,
        round(values[-1], 4),
        "percent",
        len(values),
        "rpc.qubic.org/v1/latest-stats",
        window=f"{window} snapshots",
        extra={
            "mean": round(mean, 4),
            "spread": round(values[-1] - mean, 4),
            "above_mean": values[-1] >= mean,
            "crosses_in_window": crosses,
            "percentile": percentile(values[-1], values),
            "as_of": series[-1][0],
        },
    )


def active_address_growth(stats_rows, window=6):
    """Absolute and hourly growth of active addresses over `window` snapshots."""
    metric = "active_address_growth"
    series = _stats_series(stats_rows, "active_addresses")
    if len(series) < 2:
        return refusal(metric, "need at least two snapshots", len(series), 2)
    take = series[-min(window, len(series)) :]
    delta = take[-1][1] - take[0][1]
    try:
        hours = 0 if len(take) < 2 else (int(take[-1][0]) - int(take[0][0])) / 3600
    except (TypeError, ValueError):
        hours = 0
    rates = [take[i][1] - take[i - 1][1] for i in range(1, len(take))]
    return result(
        metric,
        round(delta, 0),
        "addresses",
        len(take),
        "rpc.qubic.org/v1/latest-stats",
        window=f"{len(take)} snapshots",
        extra={
            "level": take[-1][1],
            "rate_per_hour": round(delta / hours, 2) if hours else None,
            "step_mean": round(sum(rates) / len(rates), 2) if rates else None,
            "step_z": zscore(rates[-1], rates) if rates else None,
            "percentile_of_delta": percentile(delta, rates),
            "as_of": take[-1][0],
        },
    )


def burn_intensity(stats_rows, window=6):
    """QU burned per million ticks over the trailing window of snapshots.

    Note: `burned_qus` from latest-stats is a coarse counter that does not
    advance every snapshot, so this returns 0 for long stretches. The
    authoritative per-tick series is `burn_intensity_from_events`.
    """
    metric = "burn_intensity_snapshot"
    series = []
    for row in stats_rows:
        burned = row.get("burned_qus")
        tick = row.get("current_tick")
        stamp = row.get("observed_at")
        if burned is None or tick is None or not stamp:
            continue
        try:
            series.append((stamp, float(burned), float(tick)))
        except (TypeError, ValueError):
            continue
    series.sort(key=lambda item: item[0])
    if len(series) < 2:
        return refusal(metric, "need at least two snapshots", len(series), 2)
    take = series[-min(window, len(series)) :]
    burned_delta = take[-1][1] - take[0][1]
    tick_delta = take[-1][2] - take[0][2]
    if tick_delta <= 0:
        return refusal(metric, "no tick progress inside window", len(take), 2)
    per_million = burned_delta / tick_delta * 1_000_000
    steps = []
    for index in range(1, len(take)):
        dtick = take[index][2] - take[index - 1][2]
        if dtick > 0:
            steps.append((take[index][1] - take[index - 1][1]) / dtick * 1_000_000)
    return result(
        metric,
        round(per_million, 2),
        "QU per 1e6 ticks",
        len(take),
        "rpc.qubic.org/v1/latest-stats",
        window=f"{len(take)} snapshots",
        extra={
            "burned_delta": round(burned_delta, 0),
            "tick_delta": round(tick_delta, 0),
            "step_z": zscore(steps[-1], steps) if steps else None,
            "percentile": percentile(per_million, steps),
            "as_of": take[-1][0],
        },
    )


def burn_intensity_from_events(event_rows, min_events=5):
    """Epoch burn intensity from per-tick BURNING event logs.

    Unlike the snapshot counter, event rows carry tick_number and amount, so
    the rate is meaningful immediately within the current epoch.
    """
    metric = "burn_intensity"
    usable = [
        row
        for row in event_rows
        if row.get("tick_number") not in (None, "") and row.get("burn_amount")
    ]
    if len(usable) < min_events:
        return refusal(metric, "not enough burn events yet", len(usable), min_events)
    try:
        ticks = sorted(int(row["tick_number"]) for row in usable)
        amounts = [float(row["burn_amount"]) for row in usable]
    except (TypeError, ValueError):
        return refusal(metric, "malformed burn event rows", len(usable), min_events)
    span = ticks[-1] - ticks[0]
    if span <= 0:
        return refusal(
            metric, "burn events all share one tick", len(usable), min_events
        )
    total = sum(amounts)
    epochs = {row.get("epoch") for row in usable if row.get("epoch")}
    ordered = sorted(amounts)
    return result(
        metric,
        round(total / span * 1_000_000, 2),
        "QU per 1e6 ticks",
        len(usable),
        "rpc.qubic.org/query/v1/getEventLogs (logType=8)",
        window=f"tick {ticks[0]}..{ticks[-1]}",
        extra={
            "epoch": max(epochs) if epochs else None,
            "total_burned_qu": round(total, 0),
            "tick_span": span,
            "events_per_million_ticks": round(len(usable) / span * 1_000_000, 3),
            "amount_median_qu": ordered[len(ordered) // 2],
            "amount_p90_qu": ordered[int(len(ordered) * 0.9)],
            "as_of_tick": ticks[-1],
        },
    )


def burn_profile(event_rows, initial_tick=None, scheduled_burn=None, min_events=5):
    """Epoch burn shape as four metrics instead of one misleading rate.

    Observed structure: the epoch's burn is executed as two large contract
    burns at the epoch's first tick, followed by a long trickle of small
    deductions. A uniform QU/tick average is therefore meaningless — we
    report total, schedule deviation, concentration and trickle separately.
    """
    metric = "burn_epoch_total"
    usable = [
        row
        for row in event_rows
        if row.get("tick_number") not in (None, "") and row.get("burn_amount")
    ]
    if len(usable) < min_events:
        return [refusal(metric, "not enough burn events yet", len(usable), min_events)]
    try:
        events = sorted(
            (
                (int(row["tick_number"]), float(row["burn_amount"]), row.get("epoch"))
                for row in usable
            ),
            key=lambda item: item[0],
        )
    except (TypeError, ValueError):
        return [refusal(metric, "malformed burn event rows", len(usable), min_events)]

    start = initial_tick if initial_tick is not None else events[0][0]
    amounts = [amount for _, amount, _ in events]
    total = sum(amounts)
    burst = sum(amount for tick, amount, _ in events if tick - start <= 16)
    trickle = [amount for tick, amount, _ in events if tick - start > 16]
    span = max(events[-1][0] - start, 1)
    epochs = sorted({epoch for _, _, epoch in events if epoch})
    source = "rpc.qubic.org/query/v1/getEventLogs (logType=8)"
    window = f"epoch {epochs[-1]}" if epochs else "current epoch"

    out = [
        result(
            metric,
            round(total, 0),
            "QU",
            len(events),
            source,
            window=window,
            extra={
                "epoch": epochs[-1] if epochs else None,
                "first_tick": events[0][0],
                "last_tick": events[-1][0],
                "as_of_tick": events[-1][0],
            },
        )
    ]

    if scheduled_burn and scheduled_burn > 0:
        out.append(
            result(
                "burn_deviation_vs_schedule",
                round(total / scheduled_burn, 4),
                "x observed/scheduled",
                len(events),
                source,
                window=window,
                extra={
                    "observed_burn_qu": round(total, 0),
                    "scheduled_burn_qu": round(scheduled_burn, 0),
                    "gap_qu": round(total - scheduled_burn, 0),
                    "scheduled_source": "gross_per_week × burn_rate",
                },
            )
        )
    else:
        out.append(
            refusal(
                "burn_deviation_vs_schedule",
                "no gross/burn schedule loaded",
                len(events),
                None,
            )
        )

    out.append(
        result(
            "burn_concentration_at_epoch_start",
            round(burst / total, 4),
            "share of epoch burn",
            len(events),
            source,
            window=window,
            extra={
                "burst_qu": round(burst, 0),
                "burst_events": sum(1 for tick, _, _ in events if tick - start <= 16),
                "burst_tick_window": "first 16 ticks of epoch",
            },
        )
    )

    if trickle and span > 0:
        out.append(
            result(
                "burn_trickle_rate",
                round(sum(trickle) / span * 1_000_000, 2),
                "QU per 1e6 ticks",
                len(trickle),
                source,
                window=window,
                extra={
                    "trickle_qu": round(sum(trickle), 0),
                    "tick_span": span,
                    "trickle_events": len(trickle),
                },
            )
        )
    else:
        out.append(
            refusal("burn_trickle_rate", "no post-burst events yet", len(trickle), 1)
        )
    return out


def price_hashrate_divergence(price_rows, hashrate_rows, window=30, field_note=None):
    """z(price change) − z(hashrate change) over `window` aligned periods."""
    metric = "price_hashrate_divergence"
    if not hashrate_rows:
        return refusal(metric, "no hashrate history for this chain", 0, None)

    prices = sorted(daily_closes_with(price_rows))
    hashrate = sorted(daily_closes_with(hashrate_rows))
    if len(prices) < window + 1 or len(hashrate) < window + 1:
        return refusal(
            metric,
            "history shorter than window",
            min(len(prices), len(hashrate)),
            window + 1,
        )

    price_change = pct_change(prices)
    hash_change = pct_change(hashrate)
    joined = align(price_change, hash_change)
    if len(joined) < window:
        return refusal(
            metric, "price and hashrate series barely overlap", len(joined), window
        )

    window_rows = joined[-window:]
    price_values = [row[1] for row in window_rows]
    hash_values = [row[2] for row in window_rows]
    price_z = zscore(price_values[-1], price_values)
    hash_z = zscore(hash_values[-1], hash_values)
    if price_z is None or hash_z is None:
        return refusal(metric, "zero variance inside window", len(window_rows), window)
    return result(
        metric,
        round(price_z - hash_z, 3),
        "z",
        len(window_rows),
        field_note or "price_history + chain_snapshot",
        window=f"{window} periods",
        extra={
            "price_z": price_z,
            "hashrate_z": hash_z,
            "as_of": window_rows[-1][0],
        },
    )


def metric_vs_price_corr(metric_series, price_rows, window=30, metric_name="metric"):
    """Correlation between a metric's change and price's change."""
    metric = f"{metric_name}_vs_price_corr"
    if not metric_series:
        return refusal(metric, "metric series unavailable", 0, MIN_CORR_SAMPLES)
    price_change = pct_change(sorted(daily_closes_with(price_rows)))
    metric_change = pct_change(sorted(metric_series))
    joined = align(metric_change, price_change)
    if len(joined) < MIN_CORR_SAMPLES:
        return refusal(
            metric, "not enough overlapping observations", len(joined), MIN_CORR_SAMPLES
        )
    window_rows = joined[-window:]
    value, n = pearson(
        [row[1] for row in window_rows],
        [row[2] for row in window_rows],
        min_samples=min(window, MIN_CORR_SAMPLES),
    )
    if value is None:
        return refusal(metric, "correlation undefined at this window", n, window)
    return result(
        metric,
        value,
        "r",
        n,
        metric_name,
        window=f"{len(window_rows)} periods",
        extra={"as_of": window_rows[-1][0]},
    )


def daily_closes_with(rows):
    """[(date, value)] using whichever of close/price/hashrate the row carries."""
    out = {}
    for row in rows:
        date = row.get("event_time") or row.get("date") or row.get("observed_at")
        if not date:
            continue
        key = str(date)[:10]
        for field in (
            "close_usd",
            "network_hashrate_ths",
            "network_hashrate",
            "hashrate",
            "value",
        ):
            value = row.get(field)
            if value in (None, 0):
                continue
            try:
                out[key] = float(value)
            except (TypeError, ValueError):
                continue
            break
    return sorted(out.items())
