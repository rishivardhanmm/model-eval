#!/usr/bin/env python3
"""Schema-drift checker for weekly customer-export CSVs.

Compares a baseline (known-good) export against a new export and reports:
  - missing / added / likely-renamed columns
  - row-level ID and date formatting problems
  - a severity for each finding (BREAKING / WARNING / INFO)

Read-only: never writes to either input CSV. Standard library only, so any
machine on the team can run it with no extra installs.

Usage:
    python drift_check.py BASELINE.csv NEW.csv [--out report.txt]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Column contract — mirrors the plain-language version kept in Apple Notes
# ("Customer Export - Column Contract"). Keep these two in sync by hand.
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = {
    "customer_id": r"^CUST-\d{6}$",
    "first_name": None,
    "last_name": None,
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "signup_date": r"^\d{4}-\d{2}-\d{2}$",
    "country": r"^[A-Z]{2}$",
    "status": None,
}
ALLOWED_STATUS = {"active", "inactive", "pending"}

# Columns the team has already approved as safe, non-breaking additions.
ALLOWED_NEW_COLUMNS = {"loyalty_tier"}

BREAKING = "BREAKING"
WARNING = "WARNING"
INFO = "INFO"

_SHAPE_PATTERNS = [
    ("date-iso", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("date-other", re.compile(r"^\d{1,4}[/-]\d{1,2}[/-]\d{1,4}$")),
    ("id-like", re.compile(r"^[A-Za-z]*-?\d{3,}$")),
    ("number", re.compile(r"^-?\d+(\.\d+)?$")),
]


def shape_of(value):
    """Classify a sample value so we can guess whether a missing column
    and an added column are really the same field under a new name.

    Args:
        value (str): A single raw CSV cell value to classify.

    Returns:
        str: One of "date-iso", "date-other", "id-like", "number", or "text".
    """
    for label, pattern in _SHAPE_PATTERNS:
        if pattern.match(value):
            return label
    return "text"


def read_csv(path):
    """Load one CSV file into a header list and a list of row dicts.

    Opens the file in read-only mode; this is the sole guarantee that
    the script never modifies a source export.

    Args:
        path (str): Filesystem path to the CSV file to load.

    Returns:
        tuple[list[str], list[dict]]: (column names in file order, rows as
        {column_name: value} dicts).
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def guess_renames(missing, added, baseline_rows, new_rows, sample_size=5):
    """Heuristic rename detection: pair a missing column with an added
    column if their sample values share the same shape.

    Args:
        missing (set[str]): Column names present in baseline but absent from new.
        added (set[str]): Column names present in new but absent from baseline.
        baseline_rows (list[dict]): Row dicts from the baseline file.
        new_rows (list[dict]): Row dicts from the new file.
        sample_size (int): How many leading rows to sample per column. Defaults to 5.

    Returns:
        dict[str, str]: Mapping of old (missing) column name to its guessed
        new (added) column name.
    """

    def sample_shape(rows, col):
        vals = [r.get(col, "").strip() for r in rows[:sample_size] if r.get(col, "").strip()]
        if not vals:
            return None
        return shape_of(vals[0])

    renames = {}
    unmatched_added = set(added)
    for miss_col in sorted(missing):
        miss_shape = sample_shape(baseline_rows, miss_col)
        if miss_shape is None:
            continue
        for add_col in sorted(unmatched_added):
            if sample_shape(new_rows, add_col) == miss_shape:
                renames[miss_col] = add_col
                unmatched_added.discard(add_col)
                break
    return renames


def diff_columns(baseline_fields, new_fields, baseline_rows, new_rows):
    """Compare two header rows and build every column-level finding.

    Detects likely renames first (via guess_renames), then reports any
    remaining missing columns, then any remaining added columns -
    distinguishing pre-approved additions from unannounced ones.

    Args:
        baseline_fields (list[str]): Column names from the baseline file.
        new_fields (list[str]): Column names from the new file.
        baseline_rows (list[dict]): Row dicts from the baseline file.
        new_rows (list[dict]): Row dicts from the new file.

    Returns:
        list[dict]: Finding dicts, each with "severity", "area", "message",
        and "impact" keys. Unsorted - run() sorts by severity.
    """
    baseline_set, new_set = set(baseline_fields), set(new_fields)
    missing = baseline_set - new_set
    added = new_set - baseline_set

    renames = guess_renames(missing, added, baseline_rows, new_rows)

    findings = []
    for old_name, new_name in renames.items():
        severity = BREAKING if old_name in REQUIRED_COLUMNS else WARNING
        findings.append({
            "severity": severity,
            "area": "column",
            "message": (
                f"Column '{old_name}' appears to have been renamed to '{new_name}' "
                f"(same value shape, column missing/added together)."
            ),
            "impact": (
                f"Any code referencing '{old_name}' by name (joins, sorts, filters) "
                f"will silently stop finding it."
                if severity == BREAKING
                else f"Low impact: '{old_name}' was not a required field."
            ),
        })

    renamed_old = set(renames.keys())
    renamed_new = set(renames.values())

    for col in sorted(missing - renamed_old):
        severity = BREAKING if col in REQUIRED_COLUMNS else WARNING
        findings.append({
            "severity": severity,
            "area": "column",
            "message": f"Required column '{col}' is missing from the new export." if severity == BREAKING
                       else f"Optional column '{col}' is missing from the new export.",
            "impact": "Downstream code expecting this column will error or silently produce blanks."
                       if severity == BREAKING else "Minimal impact; column was not required.",
        })

    for col in sorted(added - renamed_new):
        if col in ALLOWED_NEW_COLUMNS:
            findings.append({
                "severity": INFO,
                "area": "column",
                "message": f"New column '{col}' detected - this is on the pre-approved safe list.",
                "impact": "No action needed. Existing reports ignore unknown columns.",
            })
        else:
            findings.append({
                "severity": WARNING,
                "area": "column",
                "message": f"New column '{col}' detected - not on the pre-approved list.",
                "impact": "Probably safe (extra data), but confirm with the source team before relying on it.",
            })

    return findings


def check_row_values(fields, rows, filelabel, findings):
    """Validate customer_id, date, and status on every row of one file.

    Appends a finding dict for each malformed ID, malformed date, unexpected
    status value, and duplicate customer_id onto the shared findings list.

    Args:
        fields (list[str]): Column names present in this file.
        rows (list[dict]): Row dicts to validate.
        filelabel (str): Short label (usually the filename) used in messages.
        findings (list[dict]): Shared findings list; mutated in place.

    Returns:
        None: Findings are appended to the `findings` argument in place.
    """
    id_pattern = re.compile(REQUIRED_COLUMNS["customer_id"])
    date_col = "signup_date" if "signup_date" in fields else (
        "created_on" if "created_on" in fields else None
    )
    iso_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    seen_ids = {}

    for line_no, row in enumerate(rows, start=2):  # header is line 1
        cid = (row.get("customer_id") or "").strip()
        if cid and not id_pattern.match(cid):
            findings.append({
                "severity": BREAKING,
                "area": "row-data",
                "message": f"[{filelabel} line {line_no}] customer_id '{cid}' does not match CUST-###### format.",
                "impact": "Row will fail to join against systems keyed on the standard customer_id format.",
            })
        if cid:
            seen_ids.setdefault(cid, []).append(line_no)

        if date_col:
            val = (row.get(date_col) or "").strip()
            if val and not iso_date.match(val):
                findings.append({
                    "severity": BREAKING,
                    "area": "row-data",
                    "message": f"[{filelabel} line {line_no}] {date_col} '{val}' is not in YYYY-MM-DD format.",
                    "impact": "Date-based sorting/filtering in the weekly report will misorder or drop this row.",
                })

        status = (row.get("status") or "").strip()
        if status and status not in ALLOWED_STATUS:
            findings.append({
                "severity": WARNING,
                "area": "row-data",
                "message": f"[{filelabel} line {line_no}] status '{status}' is outside the approved set {sorted(ALLOWED_STATUS)}.",
                "impact": "Row may be miscategorized in status-based report sections.",
            })

    for cid, lines in seen_ids.items():
        if len(lines) > 1:
            findings.append({
                "severity": BREAKING,
                "area": "row-data",
                "message": f"[{filelabel}] customer_id '{cid}' repeats on lines {lines}.",
                "impact": "Duplicate IDs will double-count this customer in aggregated reports.",
            })


def run(baseline_path, new_path):
    """Load both exports and run the full column + row-level comparison.

    Args:
        baseline_path (str): Path to the known-good baseline CSV.
        new_path (str): Path to the new (possibly drifted) CSV.

    Returns:
        tuple[list[str], list[str], list[dict]]: (baseline column names,
        new-file column names, findings sorted most-severe first).
    """
    baseline_fields, baseline_rows = read_csv(baseline_path)
    new_fields, new_rows = read_csv(new_path)

    findings = diff_columns(baseline_fields, new_fields, baseline_rows, new_rows)
    check_row_values(new_fields, new_rows, Path(new_path).name, findings)

    order = {BREAKING: 0, WARNING: 1, INFO: 2}
    findings.sort(key=lambda f: order[f["severity"]])
    return baseline_fields, new_fields, findings


def render_report(baseline_path, new_path, baseline_fields, new_fields, findings):
    """Format a findings list into the fixed-width text report.

    Args:
        baseline_path (str): Path to the baseline CSV (shown in the header).
        new_path (str): Path to the new CSV (shown in the header).
        baseline_fields (list[str]): Baseline column names, for display.
        new_fields (list[str]): New-file column names, for display.
        findings (list[dict]): Findings to render, most-severe first.

    Returns:
        str: The complete report text, ready to print or write to a file.
    """
    lines = []
    lines.append("=" * 72)
    lines.append("SCHEMA-DRIFT REPORT")
    lines.append("=" * 72)
    lines.append(f"Baseline file : {baseline_path}")
    lines.append(f"New file      : {new_path}")
    lines.append(f"Baseline cols : {', '.join(baseline_fields)}")
    lines.append(f"New cols      : {', '.join(new_fields)}")
    lines.append("")

    counts = {BREAKING: 0, WARNING: 0, INFO: 0}
    for f in findings:
        counts[f["severity"]] += 1
    lines.append(
        f"Summary: {counts[BREAKING]} breaking, {counts[WARNING]} need review, {counts[INFO]} informational"
    )
    lines.append("-" * 72)

    if not findings:
        lines.append("No drift detected. New export matches the column contract.")
    else:
        for f in findings:
            lines.append(f"[{f['severity']:9s}] {f['message']}")
            lines.append(f"            Likely impact: {f['impact']}")
            lines.append("")

    lines.append("=" * 72)
    lines.append("Source files were opened read-only; neither CSV was modified by this run.")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    """CLI entry point: parse arguments, run the check, print/save the
    report, and exit non-zero if any BREAKING finding was detected.

    Returns:
        None: Exits the process via sys.exit() instead of returning.
    """
    parser = argparse.ArgumentParser(description="Compare a new customer export against a known-good baseline.")
    parser.add_argument("baseline", nargs="?", default=str(Path(__file__).resolve().parent.parent / "data" / "baseline_customers.csv"))
    parser.add_argument("new", nargs="?", default=str(Path(__file__).resolve().parent.parent / "data" / "drifted_customers.csv"))
    parser.add_argument("--out", help="Also write the report to this file.")
    args = parser.parse_args()

    baseline_fields, new_fields, findings = run(args.baseline, args.new)
    report = render_report(args.baseline, args.new, baseline_fields, new_fields, findings)

    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"\nReport also written to {args.out}")

    has_breaking = any(f["severity"] == BREAKING for f in findings)
    sys.exit(1 if has_breaking else 0)


if __name__ == "__main__":
    main()
