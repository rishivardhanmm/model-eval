"""Synthetic numeric stream for the telemetry tool (latencies in milliseconds)."""

import random

DOMAIN_MS = (0.0, 1000.0)


def generate_stream(n, seed):
    """Generate a reproducible stream of uniform request latencies.

    Args:
        n: Number of values to generate.
        seed: Seed for the random generator; the same seed gives the same stream.

    Returns:
        A list of n floats in DOMAIN_MS.
    """
    rng = random.Random(seed)
    low, high = DOMAIN_MS
    return [rng.uniform(low, high) for _ in range(n)]
