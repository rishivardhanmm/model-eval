"""Compare KLL sketch estimates of p50/p95 with exact quantiles; write CSV and SVG plot."""

# csv writes the results table without any third-party package
import csv
# math.log10 places stream lengths on a log-scale x axis
import math
# random builds the seeded skewed stream
import random
# Path keeps output paths relative to this script, wherever it is run from
from pathlib import Path

# The new approximate summary (annotated copy; identical logic to kll_sketch.py)
from kll_sketch_annotated import KLLSketch
# The existing stream generator and its bounded 0-1000 ms value domain
from streams import DOMAIN_MS, generate_stream
# The existing exact quantile, used as ground truth
from telemetry_stats import exact_quantile

# Fixed seed for every stream, so the data is identical on every run
STREAM_SEED = 7
# Fixed seed for the sketch's coin flips, so the summary is identical on every run
SKETCH_SEED = 42
# The k used for the pass/fail checks
CONFIGURED_K = 200
# Extra k values that show the accuracy-vs-memory trade-off
K_SWEEP = (50, 100, 200)
# Growing stream lengths, to show memory stays bounded as n grows
LENGTHS = (1_000, 10_000, 100_000)
# The two quantiles the telemetry tool reports: p50 and p95
QUANTILES = (0.5, 0.95)
# Absolute error budget in ms, derived from KLL's ~1.65% rank error (see README)
TOLERANCE_MS = 35.0
# The four stream shapes named in the check
STREAM_KINDS = ("uniform", "skewed", "constant", "sorted")
# Results land next to the script in results/
OUT_DIR = Path(__file__).parent / "results"
# Fixed color per stream (validated categorical palette, slots 1-4)
COLORS = {"uniform": "#2a78d6", "skewed": "#eb6834", "constant": "#1baf7a", "sorted": "#eda100"}
# A distinct marker shape per stream, so the plot never relies on color alone
SHAPES = {"uniform": "circle", "skewed": "square", "constant": "triangle", "sorted": "diamond"}


def build_stream(kind, n, seed):
    """Build one fixed-seed synthetic stream inside DOMAIN_MS.

    Args:
        kind: One of STREAM_KINDS.
        n: Stream length.
        seed: Seed so the same stream is rebuilt on every run.

    Returns:
        A list of n floats.
    """
    # Uniform: the existing generator, unchanged
    if kind == "uniform":
        return generate_stream(n, seed)
    # Skewed: exponential latencies (mean 100 ms), long right tail
    if kind == "skewed":
        # Own seeded generator so the skewed stream is reproducible too
        rng = random.Random(seed)
        # Clip to the domain ceiling so every stream stays bounded
        return [min(rng.expovariate(1 / 100), DOMAIN_MS[1]) for _ in range(n)]
    # Constant: every value identical, so the sketch must be exact
    if kind == "constant":
        return [250.0] * n
    # Sorted: same values as uniform, arriving in ascending order (adversarial order)
    if kind == "sorted":
        return sorted(generate_stream(n, seed))
    # Guard against typos in the stream name
    raise ValueError(f"unknown stream kind: {kind}")


def summarize(stream, k):
    """Feed a stream through a fresh sketch.

    Args:
        stream: List of values.
        k: Sketch accuracy parameter.

    Returns:
        The populated KLLSketch.
    """
    # A fresh sketch with the fixed seed
    sketch = KLLSketch(k=k, seed=SKETCH_SEED)
    # One value at a time, exactly as a live stream would arrive
    for value in stream:
        sketch.update(value)
    # Hand back the summary; the stream itself is no longer needed by the sketch
    return sketch


def run_case(kind, n, k):
    """Compare sketch and exact quantiles for one stream, length and k.

    Args:
        kind: Stream kind.
        n: Stream length.
        k: Sketch accuracy parameter.

    Returns:
        A dict holding one CSV row.
    """
    # Build the stream (kept in full only so we can compute the exact answer)
    stream = build_stream(kind, n, STREAM_SEED)
    # Summarize it with the sketch
    sketch = summarize(stream, k)
    # Rebuild from the same seeds to prove the summary is reproducible
    rerun = summarize(build_stream(kind, n, STREAM_SEED), k)
    # Start the CSV row with what identifies this case
    row = {"stream": kind, "n": n, "k": k}
    # Compare p50 and p95
    for q in QUANTILES:
        # Column name suffix: p50 or p95
        name = f"p{round(q * 100)}"
        # Ground truth from the existing exact function
        exact = exact_quantile(stream, q)
        # Approximation from the sketch
        estimate = sketch.quantile(q)
        # Rounded to 3 decimals so the CSV is readable and byte-stable
        row[f"exact_{name}"] = round(exact, 3)
        row[f"est_{name}"] = round(estimate, 3)
        # The absolute error the check asks for
        row[f"abs_err_{name}"] = round(abs(estimate - exact), 3)
    # Record the tolerance on every row so the CSV stands on its own
    row["tolerance_ms"] = TOLERANCE_MS
    # Pass only if both p50 and p95 are inside the tolerance
    row["within_tolerance"] = max(row["abs_err_p50"], row["abs_err_p95"]) <= TOLERANCE_MS
    # Estimates must never cross: p50 <= p95
    row["monotonic"] = sketch.quantile(0.5) <= sketch.quantile(0.95)
    # Items held at the end of the stream
    row["retained_items"] = sketch.size
    # Highest item count at any moment while streaming (the real memory peak)
    row["peak_items"] = sketch.peak_size
    # The configured hard cap, 3k + 64
    row["memory_bound"] = sketch.memory_bound()
    # Memory check: the peak never exceeded the cap
    row["within_bound"] = sketch.peak_size <= sketch.memory_bound()
    # Fingerprint of the whole summary state
    row["digest"] = sketch.digest()
    # Reproducibility check: identical state from identical seeds
    row["reproducible"] = sketch.digest() == rerun.digest()
    # One finished CSV row
    return row


def marker(kind, x, y):
    """Return the SVG shape used for one stream, so identity is not color alone.

    Args:
        kind: Stream kind.
        x: Center x in pixels.
        y: Center y in pixels.

    Returns:
        An SVG element string.
    """
    # Uniform: circle
    if SHAPES[kind] == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5"/>'
    # Skewed: square
    if SHAPES[kind] == "square":
        return f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" rx="1"/>'
    # Constant: triangle
    if SHAPES[kind] == "triangle":
        return f'<path d="M{x:.1f},{y - 5:.1f} L{x + 5:.1f},{y + 4:.1f} L{x - 5:.1f},{y + 4:.1f} Z"/>'
    # Sorted: diamond
    return f'<path d="M{x:.1f},{y - 5.5:.1f} L{x + 5.5:.1f},{y:.1f} L{x:.1f},{y + 5.5:.1f} L{x - 5.5:.1f},{y:.1f} Z"/>'


def plot_svg(rows, path):
    """Draw absolute error vs stream length, one panel each for p50 and p95.

    Args:
        rows: Result rows for the configured k.
        path: Output .svg path.
    """
    # Canvas size and margins in pixels
    width, height, pad_l, pad_t, pad_b, gap = 920, 400, 56, 92, 48, 70
    # Two side-by-side panels share the width
    panel_w = (width - 2 * pad_l - gap) / 2
    # Vertical space for the data
    plot_h = height - pad_t - pad_b
    # y axis tops out a little above the tolerance so the dashed line is visible
    y_max = TOLERANCE_MS * 1.25
    # x axis is log10 of stream length
    x_lo, x_hi = math.log10(LENGTHS[0]), math.log10(LENGTHS[-1])

    # Map a stream length to an x pixel inside a panel (room on the right for labels)
    def sx(left, n):
        return left + 20 + (math.log10(n) - x_lo) / (x_hi - x_lo) * (panel_w - 110)

    # Map an error in ms to a y pixel (0 at the bottom, clipped at the top)
    def sy(err):
        return pad_t + plot_h - min(err, y_max) / y_max * plot_h

    # Header: SVG root, light/dark theme styles, background and title
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Segoe UI, Arial, sans-serif">',
        "<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}.axis{stroke:#8a8984}.tol{stroke:#52514e}"
        " @media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}.grid{stroke:#33332f}.axis{stroke:#6d6c66}.tol{stroke:#c3c2b7}}</style>",
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="t1" x="{pad_l}" y="26" font-size="16" font-weight="600">KLL sketch vs exact quantiles: absolute error (ms), k={CONFIGURED_K}, stream seed {STREAM_SEED}</text>',
    ]
    # Legend row starts at the left margin
    legend_x = pad_l
    # One legend entry (shape + name) per stream
    for kind in STREAM_KINDS:
        out.append(f'<g fill="{COLORS[kind]}">{marker(kind, legend_x + 5, 48)}</g>')
        out.append(f'<text class="t2" x="{legend_x + 15}" y="52" font-size="12">{kind}</text>')
        legend_x += 90
    # Legend entry for the dashed tolerance line
    out.append(f'<line class="tol" x1="{legend_x + 4}" y1="48" x2="{legend_x + 28}" y2="48" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text class="t2" x="{legend_x + 34}" y="52" font-size="12">tolerance {TOLERANCE_MS:g} ms</text>')
    # One panel per quantile
    for i, q in enumerate(QUANTILES):
        # p50 or p95
        name = f"p{round(q * 100)}"
        # Left edge of this panel
        left = pad_l + i * (panel_w + gap)
        # Panel title
        out.append(f'<text class="t1" x="{left}" y="{pad_t - 4}" font-size="13" font-weight="600">{name}</text>')
        # Recessive gridlines and y tick labels every 10 ms
        for tick in range(0, int(y_max) + 1, 10):
            y = sy(tick)
            out.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + panel_w}" y2="{y:.1f}" stroke-width="1"/>')
            out.append(f'<text class="t2" x="{left - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end">{tick}</text>')
        # Baseline at zero error
        out.append(f'<line class="axis" x1="{left}" y1="{sy(0):.1f}" x2="{left + panel_w}" y2="{sy(0):.1f}" stroke-width="1"/>')
        # x tick labels: the three stream lengths
        for n in LENGTHS:
            out.append(f'<text class="t2" x="{sx(left, n):.1f}" y="{sy(0) + 18:.1f}" font-size="11" text-anchor="middle">{n:,}</text>')
        # x axis title
        out.append(f'<text class="t2" x="{left + panel_w / 2:.1f}" y="{height - 8}" font-size="11" text-anchor="middle">stream length (log scale)</text>')
        # Dashed tolerance line: every point below it passes
        out.append(f'<line class="tol" x1="{left}" y1="{sy(TOLERANCE_MS):.1f}" x2="{left + panel_w}" y2="{sy(TOLERANCE_MS):.1f}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        # Collect end-of-line label positions so they can be de-overlapped
        labels = []
        # One line per stream
        for kind in STREAM_KINDS:
            # Pixel position of each (length, error) point for this stream
            points = [(sx(left, r["n"]), sy(r[f"abs_err_{name}"]), r) for r in rows if r["stream"] == kind]
            # Join points into an SVG polyline
            line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            out.append(f'<polyline points="{line}" fill="none" stroke="{COLORS[kind]}" stroke-width="2" stroke-linejoin="round"/>')
            # A marker per point, with a hover tooltip showing exact, estimate and error
            for x, y, r in points:
                tip = f'{kind}, n={r["n"]:,}: exact {r[f"exact_{name}"]} ms, estimate {r[f"est_{name}"]} ms, error {r[f"abs_err_{name}"]} ms'
                out.append(f'<g fill="{COLORS[kind]}"><title>{tip}</title>{marker(kind, x, y)}</g>')
            # Remember where this line ends, for its direct label
            labels.append([points[-1][1], kind])
        # Bottom-most label first
        labels.sort(reverse=True)
        # Push each label up so labels sit at least 13 px apart
        for j in range(1, len(labels)):
            labels[j][0] = min(labels[j][0], labels[j - 1][0] - 13)
        # Draw the direct labels to the right of the last point
        for y, kind in labels:
            out.append(f'<text class="t2" x="{sx(left, LENGTHS[-1]) + 12:.1f}" y="{y + 4:.1f}" font-size="11">{kind}</text>')
    # Close the SVG
    out.append("</svg>")
    # Write with a fixed encoding and newline so the file is byte-identical across runs
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    """Run every case, write the CSV and SVG, and print a pass/fail summary."""
    # Make sure results/ exists
    OUT_DIR.mkdir(exist_ok=True)
    # Every k x stream x length combination
    rows = [run_case(kind, n, k) for k in K_SWEEP for kind in STREAM_KINDS for n in LENGTHS]
    # Write the CSV; newline="" avoids blank lines on Windows
    with open(OUT_DIR / "quantile_comparison.csv", "w", newline="", encoding="utf-8") as f:
        # Columns come from the row dict, in insertion order
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Pass/fail checks use only the configured k
    configured = [r for r in rows if r["k"] == CONFIGURED_K]
    # Plot error for the configured k
    plot_svg(configured, OUT_DIR / "accuracy_plot.svg")
    # Terminal summary header
    print(f"{'stream':<9}{'n':>8}{'err p50':>9}{'err p95':>9}  tol   mono  peak/bound  repro")
    # One line per case: errors, tolerance, monotonic, memory, reproducibility
    for r in configured:
        print(f"{r['stream']:<9}{r['n']:>8}{r['abs_err_p50']:>9.3f}{r['abs_err_p95']:>9.3f}  "
              f"{'ok' if r['within_tolerance'] else 'FAIL':<5} {'ok' if r['monotonic'] else 'FAIL':<5}"
              f"{r['peak_items']:>4}/{r['memory_bound']:<6} {'ok' if r['reproducible'] else 'FAIL'}")
    # The four checks from the task
    checks = ("within_tolerance", "monotonic", "within_bound", "reproducible")
    # Everything must pass for the configured k
    passed = all(r[c] for r in configured for c in checks)
    # Overall verdict
    print(f"\nk={CONFIGURED_K}: {'ALL CHECKS PASS' if passed else 'SOME CHECKS FAILED'}")
    # Trade-off table: memory vs accuracy for each k at the longest stream
    print(f"\nAccuracy vs memory at n={LENGTHS[-1]:,} (worst error across streams):")
    for k in K_SWEEP:
        # Rows for this k at the largest n
        sweep = [r for r in rows if r["k"] == k and r["n"] == LENGTHS[-1]]
        # Worst p50/p95 error across the four streams
        worst = max(max(r["abs_err_p50"], r["abs_err_p95"]) for r in sweep)
        print(f"  k={k:<4} peak items {max(r['peak_items'] for r in sweep):>4}  worst abs error {worst:7.3f} ms")


# Run only when executed directly, not when imported
if __name__ == "__main__":
    main()
