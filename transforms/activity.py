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
