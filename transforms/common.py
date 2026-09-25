"""Pure series helpers for insight transforms.

No I/O, no fetching: every function takes lists and returns dicts. Anything a
caller cannot compute honestly returns a refusal record instead of a number,
per the garden rule "missing data stays missing".
"""

TRANSFORM_VERSION = "insights-v1"

MIN_CORR_SAMPLES = 30
MIN_PUELL_SAMPLES = 200
MIN_RIBBON_SAMPLES = 13


def refusal(metric, reason, have=0, need=None):
    """A metric we will not compute yet. Never emit a placeholder value."""
    return {
        "metric": metric,
        "refused": True,
        "reason": reason,
        "n": have,
        "min_n": need,
        "version": TRANSFORM_VERSION,
    }


def daily_closes(rows):
    """[(date, close)] from price_history rows, one value per UTC date."""
    out = {}
    for row in rows:
        date = row.get("date")
        close = row.get("close_usd")
        if not date or close in (None, 0):
            continue
        try:
            out[date] = float(close)
        except (TypeError, ValueError):
            continue
    return sorted(out.items())


def rolling_mean(values, window):
    """Trailing mean, None until `window` observations exist."""
    if window <= 0 or len(values) < window:
        return None
    tail = values[-window:]
    return sum(tail) / window


def percentile(value, population):
    if value is None or not population:
        return None
    below = sum(1 for item in population if item <= value)
    return round(below / len(population) * 100, 1)


def zscore(value, population):
    if value is None or not population:
        return None
    mean = sum(population) / len(population)
    variance = sum((item - mean) ** 2 for item in population) / len(population)
    deviation = variance**0.5
    if deviation < 1e-12:
        return 0.0
    return round((value - mean) / deviation, 3)


def pearson(xs, ys, min_samples=MIN_CORR_SAMPLES):
    """Correlation of aligned series. Refuses below `min_samples`."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < min_samples:
        return None, len(pairs)
    if len({p[0] for p in pairs}) < 2 or len({p[1] for p in pairs}) < 2:
        return None, len(pairs)
    n = len(pairs)
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    cov = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    vx = sum((p[0] - mx) ** 2 for p in pairs)
    vy = sum((p[1] - my) ** 2 for p in pairs)
    denom = (vx * vy) ** 0.5
    if denom < 1e-12:
        return None, n
    return round(cov / denom, 4), n


def pct_change(series):
    """Aligned percentage changes for [(date, value)] series."""
    out = []
    for index in range(1, len(series)):
        previous, current = series[index - 1][1], series[index][1]
        if previous in (None, 0):
            out.append((series[index][0], None))
            continue
        out.append((series[index][0], (current - previous) / previous))
    return out


def align(a, b):
    """Join two [(date, value)] series on date, preserving order of `a`."""
    lookup = dict(b)
    return [
        (date, value, lookup.get(date))
        for date, value in a
        if date in lookup and value is not None and lookup[date] is not None
    ]


def result(metric, value, unit, n, source, window=None, extra=None):
    payload = {
        "metric": metric,
        "value": value,
        "unit": unit,
        "n": n,
        "window": window,
        "source": source,
        "refused": False,
        "version": TRANSFORM_VERSION,
    }
    if extra:
        payload.update(extra)
    return payload
