"""Activity transforms — measured network activity from transfer windows.

Complements the official coarse counters: `activeAddresses` in
`/v1/latest-stats` did not change across sixteen minutes of five-minute
snapshots, so we measure unique addresses inside a real transfer window
instead.

Inputs are rows from `qubic_transfer_window` (one per collector pass).
Pure functions, no I/O.
"""

from transforms.common import refusal, result


def _latest(rows, count=1):
    ordered = sorted(rows, key=lambda row: row.get("observed_at") or "")
    return ordered[-count:] if count > 1 else ordered[-1:]


def activity_metrics(rows, previous_count=1):
    """Metric list for the newest transfer window, plus a delta vs prior."""
    metric = "measured_active_addresses"
    ordered = _latest(rows)
    if not ordered:
        return [refusal(metric, "no transfer windows collected yet", 0, 1)]
    row = ordered[-1]
    addresses = row.get("unique_addresses")
    if addresses is None:
        return [refusal(metric, "window has no address count", 0, 1)]

    transfers = row.get("n_transfers") or 0
    window_seconds = row.get("window_seconds")
    source = "rpc.qubic.org/query/v1/getEventLogs (logType=0)"
    window = (f"{row.get('tick_from')}..{row.get('tick_to')} ticks"
              if row.get("tick_from") is not None else "rolling window")

    out = [result(metric, int(addresses), "addresses in window", transfers,
                  source, window=window,
                  extra={"window_seconds": window_seconds,
                         "tick_from": row.get("tick_from"),
                         "tick_to": row.get("tick_to"),
                         "epoch": row.get("epoch"),
                         "note": "measured from quTransfer source+destination"})]

    if window_seconds and window_seconds > 0:
        out.append(result(
            "transfer_rate",
            round(transfers / window_seconds * 60, 2),
            "transfers/min", transfers, source, window=window,
            extra={"window_seconds": window_seconds,
                   "transfers": transfers}))

    inflow = row.get("exchange_inflow") or 0
    outflow = row.get("exchange_outflow") or 0
    netflow = row.get("exchange_netflow")
    netflow_metric = result(
        "exchange_netflow", netflow, "QU net in window", transfers,
        source, window=window,
        extra={"exchange_inflow": inflow, "exchange_outflow": outflow,
               "sign_convention": "positive = net outflow from exchanges"})
    previous = _latest(rows, previous_count + 1)
    if len(previous) > 1:
        prior = previous[0]
        if prior.get("exchange_netflow") is not None and netflow is not None:
            netflow_metric["netflow_delta"] = netflow - prior["exchange_netflow"]
    out.append(netflow_metric)

    whale_share = row.get("whale_share_of_volume")
    if whale_share is not None:
        out.append(result(
            "whale_share_of_volume", whale_share, "share of window volume",
            row.get("whale_count") or 0, source, window=window,
            extra={"whale_count": row.get("whale_count"),
                   "whale_volume": row.get("whale_volume"),
                   "threshold_qu": 1_000_000_000}))
    return out


def _bucket_seconds(key, bucket=300):
    """Fold an ISO timestamp or unix seconds into a fixed time bucket."""
    import datetime as _dt

    if isinstance(key, (int, float)):
        seconds = float(key)
        if seconds > 1e12:
            seconds /= 1000
    elif isinstance(key, str):
        stripped = key.strip()
        if stripped.isdigit():
            seconds = float(stripped)
            if seconds > 1e12:
                seconds /= 1000
            return int(seconds // bucket) * bucket
        text = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
        try:
            seconds = _dt.datetime.fromisoformat(text).timestamp()
        except ValueError:
            return None
    else:
        return None
    return int(seconds // bucket) * bucket


def intraday_price_correlation(activity_rows, price_rows, bucket=300,
                               min_samples=12, activity_field="unique_addresses"):
    """Correlation of network activity with price inside the same time buckets.

    QUBIC hashrate is not exposed by any public endpoint, so we correlate the
    activity we can measure (transfers, unique addresses) against venue mids
    over 5-minute buckets. This needs only hours of history, not days.
    """
    metric = "activity_vs_price_corr"
    activity = {}
    for row in activity_rows:
        value = row.get(activity_field)
        if value is None:
            continue
        key = _bucket_seconds(row.get("observed_at"), bucket)
        if key is not None:
            activity[key] = float(value)
    prices = {}
    for row in price_rows:
        mid = row.get("mid")
        if mid is None:
            continue
        key = _bucket_seconds(row.get("observed_at") or row.get("receive_time"),
                              bucket)
        if key is not None:
            prices[key] = float(mid)
    joined = [(key, activity[key], prices[key]) for key in sorted(activity)
              if key in prices]
    if len(joined) < min_samples:
        return refusal(metric, "not enough overlapping time buckets",
                       len(joined), min_samples)
    window = joined[-min_samples:]
    xs = [row[1] for row in window]
    ys = [row[2] for row in window]
    n = len(window)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    if denom < 1e-12 or var_x < 1e-12 or var_y < 1e-12:
        return refusal(metric, "zero variance inside window", n, min_samples)
    return result(
        metric, round(cov / denom, 4), "r", n,
        "qubic-eventlog × SafeTrade orderbook mid",
        window=f"{len(window)} × {bucket}s buckets",
        extra={"activity_field": activity_field,
               "first_bucket": window[0][0], "last_bucket": window[-1][0]},
    )
