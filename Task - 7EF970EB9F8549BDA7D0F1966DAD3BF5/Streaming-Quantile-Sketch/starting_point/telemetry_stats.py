"""Exact summary statistics for the telemetry tool."""

import math


def exact_quantile(values, q):
    """Return the exact nearest-rank quantile of a list of numbers.

    Args:
        values: Non-empty list of numbers (the full stream, held in memory).
        q: Quantile in the range (0, 1], e.g. 0.5 for p50 or 0.95 for p95.

    Returns:
        The value at rank ceil(q * n) in sorted order.
    """
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]
