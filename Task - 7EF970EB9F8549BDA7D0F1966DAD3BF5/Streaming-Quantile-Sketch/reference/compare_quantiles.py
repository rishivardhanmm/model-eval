"""Compare KLL sketch estimates of p50/p95 with exact quantiles; write CSV and SVG plot."""

import csv
import math
import random
from pathlib import Path

from kll_sketch import KLLSketch
from streams import DOMAIN_MS, generate_stream
from telemetry_stats import exact_quantile

STREAM_SEED = 7
SKETCH_SEED = 42
CONFIGURED_K = 200
K_SWEEP = (50, 100, 200)
LENGTHS = (1_000, 10_000, 100_000)
QUANTILES = (0.5, 0.95)
TOLERANCE_MS = 35.0
STREAM_KINDS = ("uniform", "skewed", "constant", "sorted")
OUT_DIR = Path(__file__).parent / "results"
COLORS = {"uniform": "#2a78d6", "skewed": "#eb6834", "constant": "#1baf7a", "sorted": "#eda100"}
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
    if kind == "uniform":
        return generate_stream(n, seed)
    if kind == "skewed":
        rng = random.Random(seed)
        return [min(rng.expovariate(1 / 100), DOMAIN_MS[1]) for _ in range(n)]
    if kind == "constant":
        return [250.0] * n
    if kind == "sorted":
        return sorted(generate_stream(n, seed))
    raise ValueError(f"unknown stream kind: {kind}")


def summarize(stream, k):
    """Feed a stream through a fresh sketch.

    Args:
        stream: List of values.
        k: Sketch accuracy parameter.

    Returns:
        The populated KLLSketch.
    """
    sketch = KLLSketch(k=k, seed=SKETCH_SEED)
    for value in stream:
        sketch.update(value)
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
    stream = build_stream(kind, n, STREAM_SEED)
    sketch = summarize(stream, k)
    rerun = summarize(build_stream(kind, n, STREAM_SEED), k)
    row = {"stream": kind, "n": n, "k": k}
    for q in QUANTILES:
        name = f"p{round(q * 100)}"
        exact = exact_quantile(stream, q)
        estimate = sketch.quantile(q)
        row[f"exact_{name}"] = round(exact, 3)
        row[f"est_{name}"] = round(estimate, 3)
        row[f"abs_err_{name}"] = round(abs(estimate - exact), 3)
    row["tolerance_ms"] = TOLERANCE_MS
    row["within_tolerance"] = max(row["abs_err_p50"], row["abs_err_p95"]) <= TOLERANCE_MS
    row["monotonic"] = sketch.quantile(0.5) <= sketch.quantile(0.95)
    row["retained_items"] = sketch.size
    row["peak_items"] = sketch.peak_size
    row["memory_bound"] = sketch.memory_bound()
    row["within_bound"] = sketch.peak_size <= sketch.memory_bound()
    row["digest"] = sketch.digest()
    row["reproducible"] = sketch.digest() == rerun.digest()
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
    if SHAPES[kind] == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5"/>'
    if SHAPES[kind] == "square":
        return f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" rx="1"/>'
    if SHAPES[kind] == "triangle":
        return f'<path d="M{x:.1f},{y - 5:.1f} L{x + 5:.1f},{y + 4:.1f} L{x - 5:.1f},{y + 4:.1f} Z"/>'
    return f'<path d="M{x:.1f},{y - 5.5:.1f} L{x + 5.5:.1f},{y:.1f} L{x:.1f},{y + 5.5:.1f} L{x - 5.5:.1f},{y:.1f} Z"/>'


def plot_svg(rows, path):
    """Draw absolute error vs stream length, one panel each for p50 and p95.

    Args:
        rows: Result rows for the configured k.
        path: Output .svg path.
    """
    width, height, pad_l, pad_t, pad_b, gap = 920, 400, 56, 92, 48, 70
    panel_w = (width - 2 * pad_l - gap) / 2
    plot_h = height - pad_t - pad_b
    y_max = TOLERANCE_MS * 1.25
    x_lo, x_hi = math.log10(LENGTHS[0]), math.log10(LENGTHS[-1])

    def sx(left, n):
        return left + 20 + (math.log10(n) - x_lo) / (x_hi - x_lo) * (panel_w - 110)

    def sy(err):
        return pad_t + plot_h - min(err, y_max) / y_max * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Segoe UI, Arial, sans-serif">',
        "<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}.axis{stroke:#8a8984}.tol{stroke:#52514e}"
        " @media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}.grid{stroke:#33332f}.axis{stroke:#6d6c66}.tol{stroke:#c3c2b7}}</style>",
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="t1" x="{pad_l}" y="26" font-size="16" font-weight="600">KLL sketch vs exact quantiles: absolute error (ms), k={CONFIGURED_K}, stream seed {STREAM_SEED}</text>',
    ]
    legend_x = pad_l
    for kind in STREAM_KINDS:
        out.append(f'<g fill="{COLORS[kind]}">{marker(kind, legend_x + 5, 48)}</g>')
        out.append(f'<text class="t2" x="{legend_x + 15}" y="52" font-size="12">{kind}</text>')
        legend_x += 90
    out.append(f'<line class="tol" x1="{legend_x + 4}" y1="48" x2="{legend_x + 28}" y2="48" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text class="t2" x="{legend_x + 34}" y="52" font-size="12">tolerance {TOLERANCE_MS:g} ms</text>')
    for i, q in enumerate(QUANTILES):
        name = f"p{round(q * 100)}"
        left = pad_l + i * (panel_w + gap)
        out.append(f'<text class="t1" x="{left}" y="{pad_t - 4}" font-size="13" font-weight="600">{name}</text>')
        for tick in range(0, int(y_max) + 1, 10):
            y = sy(tick)
            out.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + panel_w}" y2="{y:.1f}" stroke-width="1"/>')
            out.append(f'<text class="t2" x="{left - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end">{tick}</text>')
        out.append(f'<line class="axis" x1="{left}" y1="{sy(0):.1f}" x2="{left + panel_w}" y2="{sy(0):.1f}" stroke-width="1"/>')
        for n in LENGTHS:
            out.append(f'<text class="t2" x="{sx(left, n):.1f}" y="{sy(0) + 18:.1f}" font-size="11" text-anchor="middle">{n:,}</text>')
        out.append(f'<text class="t2" x="{left + panel_w / 2:.1f}" y="{height - 8}" font-size="11" text-anchor="middle">stream length (log scale)</text>')
        out.append(f'<line class="tol" x1="{left}" y1="{sy(TOLERANCE_MS):.1f}" x2="{left + panel_w}" y2="{sy(TOLERANCE_MS):.1f}" stroke-width="1.5" stroke-dasharray="5 4"/>')
        labels = []
        for kind in STREAM_KINDS:
            points = [(sx(left, r["n"]), sy(r[f"abs_err_{name}"]), r) for r in rows if r["stream"] == kind]
            line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            out.append(f'<polyline points="{line}" fill="none" stroke="{COLORS[kind]}" stroke-width="2" stroke-linejoin="round"/>')
            for x, y, r in points:
                tip = f'{kind}, n={r["n"]:,}: exact {r[f"exact_{name}"]} ms, estimate {r[f"est_{name}"]} ms, error {r[f"abs_err_{name}"]} ms'
                out.append(f'<g fill="{COLORS[kind]}"><title>{tip}</title>{marker(kind, x, y)}</g>')
            labels.append([points[-1][1], kind])
        labels.sort(reverse=True)
        for j in range(1, len(labels)):
            labels[j][0] = min(labels[j][0], labels[j - 1][0] - 13)
        for y, kind in labels:
            out.append(f'<text class="t2" x="{sx(left, LENGTHS[-1]) + 12:.1f}" y="{y + 4:.1f}" font-size="11">{kind}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    """Run every case, write the CSV and SVG, and print a pass/fail summary."""
    OUT_DIR.mkdir(exist_ok=True)
    rows = [run_case(kind, n, k) for k in K_SWEEP for kind in STREAM_KINDS for n in LENGTHS]
    with open(OUT_DIR / "quantile_comparison.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    configured = [r for r in rows if r["k"] == CONFIGURED_K]
    plot_svg(configured, OUT_DIR / "accuracy_plot.svg")
    print(f"{'stream':<9}{'n':>8}{'err p50':>9}{'err p95':>9}  tol   mono  peak/bound  repro")
    for r in configured:
        print(f"{r['stream']:<9}{r['n']:>8}{r['abs_err_p50']:>9.3f}{r['abs_err_p95']:>9.3f}  "
              f"{'ok' if r['within_tolerance'] else 'FAIL':<5} {'ok' if r['monotonic'] else 'FAIL':<5}"
              f"{r['peak_items']:>4}/{r['memory_bound']:<6} {'ok' if r['reproducible'] else 'FAIL'}")
    checks = ("within_tolerance", "monotonic", "within_bound", "reproducible")
    passed = all(r[c] for r in configured for c in checks)
    print(f"\nk={CONFIGURED_K}: {'ALL CHECKS PASS' if passed else 'SOME CHECKS FAILED'}")
    print(f"\nAccuracy vs memory at n={LENGTHS[-1]:,} (worst error across streams):")
    for k in K_SWEEP:
        sweep = [r for r in rows if r["k"] == k and r["n"] == LENGTHS[-1]]
        worst = max(max(r["abs_err_p50"], r["abs_err_p95"]) for r in sweep)
        print(f"  k={k:<4} peak items {max(r['peak_items'] for r in sweep):>4}  worst abs error {worst:7.3f} ms")


if __name__ == "__main__":
    main()
