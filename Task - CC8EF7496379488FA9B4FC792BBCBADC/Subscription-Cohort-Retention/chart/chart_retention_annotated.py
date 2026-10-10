"""Verify the DBeaver cohort export against the database, then chart it as SVG."""

import csv  # reads the CSV that DBeaver exported
import re  # pulls the plotted values back out of the finished SVG
import sqlite3  # re-runs the same query on the database for the comparison
import sys  # optional path arguments and the exit code
from pathlib import Path  # paths that work on macOS and Windows
from xml.sax.saxutils import escape  # makes any text safe to put inside SVG markup

# The project folder is one level above chart/.
ROOT = Path(__file__).resolve().parent.parent
# This is the exact SQL file that was run in DBeaver, so there is a single source of truth.
QUERY = ROOT / "sql" / "cohort_summary.sql"
# The retention checkpoints that the query reports.
DAYS = [30, 60, 90]
# Categorical slots 1-3 (blue, orange, aqua), validated as a set for colour-blind separation.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
# The SQL rounds to 1 decimal place, so a real mismatch is at least 0.1. 0.05 absorbs "80" vs "80.0" and nothing more.
TOLERANCE = 0.05
# Every marker carries a tooltip like "2026-02 cohort, day 60: 70.0%". This regex reads it back.
POINT_TITLE = re.compile(r"<title>(\d{4}-\d{2}) cohort, day (\d+): ([\d.]+)%</title>")


def read_export(path):
    """Read the cohort summary CSV exported from DBeaver.

    Args:
        path: Path to the exported CSV (a UTF-8 byte-order mark is tolerated).

    Returns:
        A dict mapping cohort_month to a dict of column name to string value.
    """
    # utf-8-sig strips the BOM if DBeaver's "Insert BOM" option was ticked.
    with open(path, newline="", encoding="utf-8-sig") as f:
        # Key each row by its cohort. .get() turns a wrong header into a reported mismatch, not a crash.
        return {row.get("cohort_month"): row for row in csv.DictReader(f)}


def run_query(db_path):
    """Run cohort_summary.sql, the same SQL used for the DBeaver export.

    Args:
        db_path: Path to subscriptions.db.

    Returns:
        A dict mapping cohort_month to a dict of column name to value.
    """
    conn = sqlite3.connect(db_path)  # open the database the loader built
    cur = conn.execute(QUERY.read_text(encoding="utf-8"))  # one SELECT, so execute() is enough
    cols = [d[0] for d in cur.description]  # the column labels, which match the export header
    # Same shape as read_export: {cohort_month: {column: value}}.
    result = {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
    conn.close()  # release the file
    return result


def verify(exported, queried):
    """Check that every exported value equals the live query result.

    Args:
        exported: Rows from read_export.
        queried: Rows from run_query.

    Returns:
        A list of mismatch descriptions; empty when the export is verified.
    """
    problems = []  # collect every mismatch so they are all reported at once
    if set(exported) != set(queried):  # same set of cohorts on both sides?
        # key=str keeps sorting safe even if a broken header produced a None key.
        problems.append(f"cohorts differ: export {sorted(exported, key=str)} vs query {sorted(queried)}")
    for month in sorted(set(exported) & set(queried)):  # compare the cohorts that both sides have
        for col, value in queried[month].items():  # every column the query returned
            if col == "cohort_month":  # this is the key, not a value to compare
                continue
            got = exported[month].get(col)  # None means the column is missing from the export
            try:
                # Compare as numbers: DBeaver may write 80 where SQLite returns 80.0.
                same = abs(float(got) - float(value)) <= TOLERANCE
            except (TypeError, ValueError):  # a missing value, or a locale format like "80,0"
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
    width, height = 720, 440  # canvas size in pixels
    left, right, top, bottom = 64, 150, 92, 56  # margins; the right margin holds the end labels
    plot_w, plot_h = width - left - right, height - top - bottom  # the drawable area

    def x(day):
        return left + plot_w * day / 90  # day 0..90 maps across the plot width

    def y(pct):
        return top + plot_h * (1 - pct / 100)  # 100% at the top and 0% at the bottom

    parts = [
        # Root element; viewBox lets the chart scale cleanly in a browser or in VS Code.
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#fcfcfb"/>',  # light chart surface
        # The title names what is being measured.
        f'<text x="{left}" y="28" font-size="17" font-weight="600" fill="#0b0b0b">'
        "Retention by signup cohort</text>",
        # The subtitle states the definition and that the data is synthetic.
        f'<text x="{left}" y="48" font-size="12" fill="#52514e">'
        "% of accounts with no cancel event, by days since signup (synthetic data)</text>",
    ]
    for pct in range(0, 101, 25):  # quiet horizontal gridlines every 25%
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(pct)}" y2="{y(pct)}" '
                     'stroke="#e4e3df" stroke-width="1"/>')
        # Y-axis tick label, right-aligned against the plot edge.
        parts.append(f'<text x="{left - 8}" y="{y(pct) + 4}" font-size="11" fill="#52514e" '
                     f'text-anchor="end">{pct}%</text>')
    for day in [0] + DAYS:  # X-axis tick labels at the four checkpoints
        parts.append(f'<text x="{x(day)}" y="{top + plot_h + 20}" font-size="11" fill="#52514e" '
                     f'text-anchor="middle">Day {day}</text>')
    # X-axis title, centred under the plot.
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 12}" font-size="12" fill="#52514e" '
                 'text-anchor="middle">Days since signup</text>')

    for i, (month, row) in enumerate(sorted(rows.items())):  # one line per cohort, oldest first
        color = COLORS[i % len(COLORS)]  # colour follows the cohort in a fixed order
        # Every cohort starts at 100% on day 0, then the three exported checkpoints follow.
        points = [(0, 100.0)] + [(d, float(row[f"retention_{d}d_pct"])) for d in DAYS]
        path = " ".join(f"{x(d):.1f},{y(p):.1f}" for d, p in points)  # "x,y x,y ..." for polyline
        parts.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
                     'stroke-linejoin="round"/>')  # thin 2px line
        for d, p in points:  # 8px markers with a surface ring; hovering shows the exact value
            parts.append(f'<circle cx="{x(d):.1f}" cy="{y(p):.1f}" r="4" fill="{color}" '
                         f'stroke="#fcfcfb" stroke-width="2"><title>{escape(month)} cohort, '
                         f'day {d}: {p:.1f}%</title></circle>')
        last = points[-1][1]  # the 90-day value, which is the headline comparison
        # Direct label at the line end, in ink colour rather than the series colour.
        parts.append(f'<text x="{x(90) + 10}" y="{y(last) + 4}" font-size="12" fill="#0b0b0b">'
                     f'{escape(month)} · {last:.0f}%</text>')
        lx = left + i * 110  # legend entries sit side by side under the subtitle
        parts.append(f'<rect x="{lx}" y="56" width="10" height="10" rx="2" fill="{color}"/>')
        # The legend shows the cohort size, because n=10 is the main caveat.
        parts.append(f'<text x="{lx + 15}" y="65" font-size="11" fill="#52514e">'
                     f'{escape(month)} (n={row["cohort_accounts"]})</text>')
    parts.append("</svg>")  # close the root element
    return "\n".join(parts) + "\n"


def read_plotted(svg_path):
    """Read the plotted checkpoint values back out of a written chart.

    Args:
        svg_path: Path to the SVG written by build_svg.

    Returns:
        A dict mapping (cohort_month, day) to the plotted percentage, day 0 excluded.
    """
    text = svg_path.read_text(encoding="utf-8")  # read the file actually on disk, not the string in memory
    # Day 0 is the fixed 100% starting point, not a value from the export, so skip it.
    return {(m, int(d)): float(p) for m, d, p in POINT_TITLE.findall(text) if d != "0"}


def main():
    """Verify the export, write the SVG chart, and check the chart against the export.

    Returns:
        None. Exits with status 1 if either check fails.
    """
    # Default paths follow the project layout; arguments can override each one.
    export_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "exports" / "cohort_summary.csv"
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "subscriptions.db"
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "chart" / "retention_chart.svg"

    exported = read_export(export_path)  # what DBeaver wrote
    queried = run_query(db_path)  # what the database says now
    problems = verify(exported, queried)  # Check A: export compared with the query
    for problem in problems:  # list each mismatch above the FAIL line
        print("  mismatch: " + problem)
    compared = sum(len(row) - 1 for row in queried.values())  # 7 value columns x 3 cohorts = 21
    print(f"[{'FAIL' if problems else 'PASS'}] export matches cohort_summary.sql "
          f"({compared} values compared, tolerance {TOLERANCE})")
    if problems:  # never chart numbers that do not match the query
        sys.exit(1)

    # Print the exact values being plotted, so they can be read against the chart on camera.
    print(f"{'cohort':<9}{'n':>4}{'30d %':>8}{'60d %':>8}{'90d %':>8}")
    for month, row in sorted(exported.items()):
        print(f"{month:<9}{row['cohort_accounts']:>4}"
              + "".join(f"{float(row[f'retention_{d}d_pct']):>8.1f}" for d in DAYS))
    out_path.write_text(build_svg(exported), encoding="utf-8")  # SVG is plain text, with no plotting library

    plotted = read_plotted(out_path)  # Check B: what the chart file actually shows
    # Every (cohort, checkpoint) value that should appear on the chart.
    expected = {(m, d): float(row[f"retention_{d}d_pct"]) for m, row in exported.items() for d in DAYS}
    chart_ok = plotted.keys() == expected.keys() and all(  # same points, and none missing or extra
        abs(plotted[k] - expected[k]) <= TOLERANCE for k in expected)  # with the same values
    print(f"[{'PASS' if chart_ok else 'FAIL'}] chart values match export "
          f"({len(plotted)} points read back from {out_path.name})")
    if not chart_ok:
        sys.exit(1)


if __name__ == "__main__":  # run only when executed directly
    main()
