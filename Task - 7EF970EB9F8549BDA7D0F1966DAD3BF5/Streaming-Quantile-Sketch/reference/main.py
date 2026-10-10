"""Print exact p50/p95 for the generated telemetry stream."""

from streams import generate_stream
from telemetry_stats import exact_quantile

if __name__ == "__main__":
    stream = generate_stream(10_000, seed=7)
    print(f"n={len(stream)}  p50={exact_quantile(stream, 0.5):.2f} ms  p95={exact_quantile(stream, 0.95):.2f} ms")
