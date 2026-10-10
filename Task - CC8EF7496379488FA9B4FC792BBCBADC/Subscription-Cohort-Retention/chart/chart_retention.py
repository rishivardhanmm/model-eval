"""Verify the DBeaver cohort export against the database, then chart it as SVG."""

import csv
import re
import sqlite3
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
QUERY = ROOT / "sql" / "cohort_summary.sql"
DAYS = [30, 60, 90]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
TOLERANCE = 0.05
POINT_TITLE = re.compile(r"<title>(\d{4}-\d{2}) cohort, day (\d+): ([\d.]+)%</title>")


def read_export(path):
    """Read the cohort summary CSV exported from DBeaver.

    Args:
        path: Path to the exported CSV (a UTF-8 byte-order mark is tolerated).

    Returns:
        A dict mapping cohort_month to a dict of column name to string value.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {row.get("cohort_month"): row for row in csv.DictReader(f)}


def run_query(db_path):
    """Run cohort_summary.sql, the same SQL used for the DBeaver export.

    Args:
        db_path: Path to subscriptions.db.

    Returns:
        A dict mapping cohort_month to a dict of column name to value.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.execute(QUERY.read_text(encoding="utf-8"))
    cols = [d[0] for d in cur.description]
    result = {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
    conn.close()
    return result


def verify(exported, queried):
    """Check that every exported value equals the live query result.

    Args:
        exported: Rows from read_export.
        queried: Rows from run_query.

    Returns:
        A list of mismatch descriptions; empty when the export is verified.
    """
    problems = []
    if set(exported) != set(queried):
        problems.append(f"cohorts differ: export {sorted(exported, key=str)} vs query {sorted(queried)}")
    for month in sorted(set(exported) & set(queried)):
        for col, value in queried[month].items():
            if col == "cohort_month":
                continue
            got = exported[month].get(col)
            try:
                same = abs(float(got) - float(value)) <= TOLERANCE
            except (TypeError, ValueError):
                same = False
            if not same:
                problems.append(f"{month}.{col}: export {got} vs query {value}")
    return problems


def build_svg(rows):
    """Draw a retention curve per cohort: day 0 (100%) then days 30, 60, 90.

    Args:
        rows: Verified rows keyed by cohort_month.

    Returns:
        The SVG document as a string.
    """
    width, height = 720, 440
    left, right, top, bottom = 64, 150, 92, 56
    plot_w, plot_h = width - left - right, height - top - bottom

    def x(day):
        return left + plot_w * day / 90

    def y(pct):
        return top + plot_h * (1 - pct / 100)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#fcfcfb"/>',
        f'<text x="{left}" y="28" font-size="17" font-weight="600" fill="#0b0b0b">'
        "Retention by signup cohort</text>",
        f'<text x="{left}" y="48" font-size="12" fill="#52514e">'
        "% of accounts with no cancel event, by days since signup (synthetic data)</text>",
    ]
    for pct in range(0, 101, 25):
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(pct)}" y2="{y(pct)}" '
                     'stroke="#e4e3df" stroke-width="1"/>')
        parts.append(f'<text x="{left - 8}" y="{y(pct) + 4}" font-size="11" fill="#52514e" '
                     f'text-anchor="end">{pct}%</text>')
    for day in [0] + DAYS:
        parts.append(f'<text x="{x(day)}" y="{top + plot_h + 20}" font-size="11" fill="#52514e" '
                     f'text-anchor="middle">Day {day}</text>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 12}" font-size="12" fill="#52514e" '
                 'text-anchor="middle">Days since signup</text>')

    for i, (month, row) in enumerate(sorted(rows.items())):
        color = COLORS[i % len(COLORS)]
        points = [(0, 100.0)] + [(d, float(row[f"retention_{d}d_pct"])) for d in DAYS]
        path = " ".join(f"{x(d):.1f},{y(p):.1f}" for d, p in points)
        parts.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
                     'stroke-linejoin="round"/>')
        for d, p in points:
            parts.append(f'<circle cx="{x(d):.1f}" cy="{y(p):.1f}" r="4" fill="{color}" '
                         f'stroke="#fcfcfb" stroke-width="2"><title>{escape(month)} cohort, '
                         f'day {d}: {p:.1f}%</title></circle>')
        last = points[-1][1]
        parts.append(f'<text x="{x(90) + 10}" y="{y(last) + 4}" font-size="12" fill="#0b0b0b">'
                     f'{escape(month)} · {last:.0f}%</text>')
        lx = left + i * 110
        parts.append(f'<rect x="{lx}" y="56" width="10" height="10" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{lx + 15}" y="65" font-size="11" fill="#52514e">'
                     f'{escape(month)} (n={row["cohort_accounts"]})</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def read_plotted(svg_path):
    """Read the plotted checkpoint values back out of a written chart.

    Args:
        svg_path: Path to the SVG written by build_svg.

    Returns:
        A dict mapping (cohort_month, day) to the plotted percentage, day 0 excluded.
    """
    text = svg_path.read_text(encoding="utf-8")
    return {(m, int(d)): float(p) for m, d, p in POINT_TITLE.findall(text) if d != "0"}


def main():
    """Verify the export, write the SVG chart, and check the chart against the export.

    Returns:
        None. Exits with status 1 if either check fails.
    """
    export_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "exports" / "cohort_summary.csv"
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "subscriptions.db"
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "chart" / "retention_chart.svg"

    exported = read_export(export_path)
    queried = run_query(db_path)
    problems = verify(exported, queried)
    for problem in problems:
        print("  mismatch: " + problem)
    compared = sum(len(row) - 1 for row in queried.values())
    print(f"[{'FAIL' if problems else 'PASS'}] export matches cohort_summary.sql "
          f"({compared} values compared, tolerance {TOLERANCE})")
    if problems:
        sys.exit(1)

    print(f"{'cohort':<9}{'n':>4}{'30d %':>8}{'60d %':>8}{'90d %':>8}")
    for month, row in sorted(exported.items()):
        print(f"{month:<9}{row['cohort_accounts']:>4}"
              + "".join(f"{float(row[f'retention_{d}d_pct']):>8.1f}" for d in DAYS))
    out_path.write_text(build_svg(exported), encoding="utf-8")

    plotted = read_plotted(out_path)
    expected = {(m, d): float(row[f"retention_{d}d_pct"]) for m, row in exported.items() for d in DAYS}
    chart_ok = plotted.keys() == expected.keys() and all(
        abs(plotted[k] - expected[k]) <= TOLERANCE for k in expected)
    print(f"[{'PASS' if chart_ok else 'FAIL'}] chart values match export "
          f"({len(plotted)} points read back from {out_path.name})")
    if not chart_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
