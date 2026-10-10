#!/usr/bin/env python3
# Shebang so this can also be run directly on macOS/Linux as ./drift_check.py
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

import argparse          # parses the baseline/new file paths and the --out flag from the command line
import csv                # built-in CSV parsing (DictReader) - this is why no pandas install is needed
import re                 # regex matching for every ID/date/email/shape check in this file
import sys                 # used once, for sys.exit() to set the process exit code from the findings
from pathlib import Path   # cross-platform file paths, used for default sample paths and writing --out

# ---------------------------------------------------------------------------
# Column contract - mirrors the plain-language version kept in Apple Notes
# ("Customer Export - Column Contract"). Keep these two in sync by hand.
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = {
    "customer_id": r"^CUST-\d{6}$",   # must be literally "CUST-" + exactly 6 digits
    "first_name": None,                # must exist, no format to check
    "last_name": None,                 # must exist, no format to check
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",  # minimal local@domain.tld shape check
    "signup_date": r"^\d{4}-\d{2}-\d{2}$",   # strict YYYY-MM-DD only, no other layout
    "country": r"^[A-Z]{2}$",          # exactly two uppercase letters (ISO code)
    "status": None,                    # format is checked separately, against ALLOWED_STATUS below
}  # end of the column contract dict
ALLOWED_STATUS = {"active", "inactive", "pending"}  # the only valid values for the status column

# Columns the team has already approved as safe, non-breaking additions.
ALLOWED_NEW_COLUMNS = {"loyalty_tier"}  # anything in here is reported as INFO, not WARNING

BREAKING = "BREAKING"   # severity: fails the run (non-zero exit code)
WARNING = "WARNING"     # severity: needs a human to look at it, does not fail the run
INFO = "INFO"           # severity: fully expected, no action needed

# Shape patterns used ONLY to guess column renames - not for validation.
_SHAPE_PATTERNS = [
    ("date-iso", re.compile(r"^\d{4}-\d{2}-\d{2}$")),              # e.g. 2025-11-02
    ("date-other", re.compile(r"^\d{1,4}[/-]\d{1,2}[/-]\d{1,4}$")),  # e.g. 11/05/2025 or 2025/11/22
    ("id-like", re.compile(r"^[A-Za-z]*-?\d{3,}$")),               # optional letters/hyphen + 3+ digits
    ("number", re.compile(r"^-?\d+(\.\d+)?$")),                     # plain integer or decimal
]  # anything matching none of these falls through to "text" in shape_of()


def shape_of(value):
    """Classify a sample value so we can guess whether a missing column
    and an added column are really the same field under a new name.

    Args:
        value (str): A single raw CSV cell value to classify.

    Returns:
        str: One of "date-iso", "date-other", "id-like", "number", or "text".
    """
    for label, pattern in _SHAPE_PATTERNS:   # try each known shape in order
        if pattern.match(value):              # first pattern that matches wins
            return label
    return "text"                             # nothing matched - treat as plain text


def read_csv(path):
    """Load one CSV file into a header list and a list of row dicts.

    Args:
        path (str): Filesystem path to the CSV file to load.

    Returns:
        tuple[list[str], list[dict]]: (column names in file order, rows as
        {column_name: value} dicts).
    """
    # "r" (default) mode = READ-ONLY. This is what guarantees the script never
    # modifies either source CSV. utf-8-sig quietly strips an Excel BOM if present.
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)             # maps each row to {column_name: value}
        rows = list(reader)                    # materialize rows before the file closes
        return reader.fieldnames or [], rows    # fieldnames is None for an empty file - fall back to []


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
        # first N non-blank sample values for this column
        vals = [r.get(col, "").strip() for r in rows[:sample_size] if r.get(col, "").strip()]
        if not vals:
            return None                         # no usable sample data for this column
        return shape_of(vals[0])                # classify just the first sample value

    renames = {}                                 # old_name -> new_name pairs we decide are a rename
    unmatched_added = set(added)                 # added columns not yet claimed as a rename target
    for miss_col in sorted(missing):              # sorted only for deterministic output
        miss_shape = sample_shape(baseline_rows, miss_col)   # what this column looked like before
        if miss_shape is None:
            continue                              # can't guess a rename with no sample data
        for add_col in sorted(unmatched_added):
            if sample_shape(new_rows, add_col) == miss_shape:  # same shape -> likely the same field, renamed
                renames[miss_col] = add_col
                unmatched_added.discard(add_col)   # don't let two missing columns claim the same new column
                break                               # stop looking once this miss_col is matched
    return renames


def diff_columns(baseline_fields, new_fields, baseline_rows, new_rows):
    """Compare two header rows and build every column-level finding.

    Args:
        baseline_fields (list[str]): Column names from the baseline file.
        new_fields (list[str]): Column names from the new file.
        baseline_rows (list[dict]): Row dicts from the baseline file.
        new_rows (list[dict]): Row dicts from the new file.

    Returns:
        list[dict]: Finding dicts, each with "severity", "area", "message",
        and "impact" keys. Unsorted - run() sorts by severity.
    """
    baseline_set, new_set = set(baseline_fields), set(new_fields)  # header lists -> sets, for set algebra
    missing = baseline_set - new_set    # columns that disappeared
    added = new_set - baseline_set      # columns that showed up

    # Resolve likely renames FIRST, so a renamed column isn't double-reported
    # below as both "missing" and "added".
    renames = guess_renames(missing, added, baseline_rows, new_rows)

    findings = []   # every detected issue accumulates here as a dict
    for old_name, new_name in renames.items():
        # Only BREAKING if the old name was one of the 7 required contract columns;
        # a rename of some unrelated optional column is merely a WARNING.
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
        })  # end of this finding

    renamed_old = set(renames.keys())     # old names already explained by a rename above
    renamed_new = set(renames.values())   # new names already explained by a rename above

    # Anything missing that WASN'T explained by a rename gets reported on its own.
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

    # Anything new that WASN'T explained by a rename gets reported here - this is
    # where "expected new column" is split from "unannounced new column".
    for col in sorted(added - renamed_new):
        if col in ALLOWED_NEW_COLUMNS:     # pre-approved by the team as safe
            findings.append({
                "severity": INFO,
                "area": "column",
                "message": f"New column '{col}' detected - this is on the pre-approved safe list.",
                "impact": "No action needed. Existing reports ignore unknown columns.",
            })
        else:                               # not on the approved list - review, but don't fail the run
            findings.append({
                "severity": WARNING,
                "area": "column",
                "message": f"New column '{col}' detected - not on the pre-approved list.",
                "impact": "Probably safe (extra data), but confirm with the source team before relying on it.",
            })

    return findings   # unsorted - run() sorts everything by severity later


def check_row_values(fields, rows, filelabel, findings):
    """Validate customer_id, date, and status on every row of one file.

    Args:
        fields (list[str]): Column names present in this file.
        rows (list[dict]): Row dicts to validate.
        filelabel (str): Short label (usually the filename) used in messages.
        findings (list[dict]): Shared findings list; mutated in place.

    Returns:
        None: Findings are appended to the `findings` argument in place.
    """
    id_pattern = re.compile(REQUIRED_COLUMNS["customer_id"])   # reuse the contract's own regex, don't duplicate it
    # Check whichever date column name is actually present, so this keeps
    # working even after signup_date gets renamed to created_on.
    date_col = "signup_date" if "signup_date" in fields else (
        "created_on" if "created_on" in fields else None
    )
    iso_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")   # strict format check, independent of the column's name
    seen_ids = {}   # customer_id -> list of line numbers it appeared on, for duplicate detection

    for line_no, row in enumerate(rows, start=2):  # start=2: physical line 1 in the CSV is the header
        cid = (row.get("customer_id") or "").strip()      # "" if the column is missing entirely, not a crash
        if cid and not id_pattern.match(cid):               # only validate non-empty IDs
            # This is what catches 'CUST-102' (no zero-padding) and '107' (no prefix) in the sample data.
            findings.append({
                "severity": BREAKING,
                "area": "row-data",
                "message": f"[{filelabel} line {line_no}] customer_id '{cid}' does not match CUST-###### format.",
                "impact": "Row will fail to join against systems keyed on the standard customer_id format.",
            })
        if cid:
            seen_ids.setdefault(cid, []).append(line_no)   # record this ID's location for the duplicate check below

        if date_col:                                         # only check dates if a date column was found at all
            val = (row.get(date_col) or "").strip()
            if val and not iso_date.match(val):               # non-empty but wrong format
                # Catches '11/05/2025' and '2025/11/22' in the sample data.
                findings.append({
                    "severity": BREAKING,
                    "area": "row-data",
                    "message": f"[{filelabel} line {line_no}] {date_col} '{val}' is not in YYYY-MM-DD format.",
                    "impact": "Date-based sorting/filtering in the weekly report will misorder or drop this row.",
                })

        status = (row.get("status") or "").strip()
        if status and status not in ALLOWED_STATUS:   # unexpected value - flag for review, don't hard-fail
            findings.append({
                "severity": WARNING,
                "area": "row-data",
                "message": f"[{filelabel} line {line_no}] status '{status}' is outside the approved set {sorted(ALLOWED_STATUS)}.",
                "impact": "Row may be miscategorized in status-based report sections.",
            })

    # After scanning every row, look for any customer_id that showed up more than once.
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
    # Orchestration: load both files once, run both checks into the same findings list.
    baseline_fields, baseline_rows = read_csv(baseline_path)   # the known-good file
    new_fields, new_rows = read_csv(new_path)                   # this week's (possibly drifted) file

    findings = diff_columns(baseline_fields, new_fields, baseline_rows, new_rows)   # column-level findings first
    check_row_values(new_fields, new_rows, Path(new_path).name, findings)           # row-level findings appended

    order = {BREAKING: 0, WARNING: 1, INFO: 2}        # sort key: most severe first
    findings.sort(key=lambda f: order[f["severity"]])
    return baseline_fields, new_fields, findings       # handed to render_report() by main()


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
    # Pure formatting - turns the findings list into the exact text saved to drift_report.txt.
    lines = []
    lines.append("=" * 72)                              # opening banner
    lines.append("SCHEMA-DRIFT REPORT")
    lines.append("=" * 72)
    lines.append(f"Baseline file : {baseline_path}")
    lines.append(f"New file      : {new_path}")
    lines.append(f"Baseline cols : {', '.join(baseline_fields)}")   # quick visual diff against the next line
    lines.append(f"New cols      : {', '.join(new_fields)}")
    lines.append("")

    counts = {BREAKING: 0, WARNING: 0, INFO: 0}         # tally findings per severity for the summary line
    for f in findings:
        counts[f["severity"]] += 1
    lines.append(
        f"Summary: {counts[BREAKING]} breaking, {counts[WARNING]} need review, {counts[INFO]} informational"
    )
    lines.append("-" * 72)

    if not findings:
        lines.append("No drift detected. New export matches the column contract.")   # clean-run message
    else:
        for f in findings:   # one finding per 2-line block: severity+message, then impact
            lines.append(f"[{f['severity']:9s}] {f['message']}")        # :9s aligns BREAKING/WARNING/INFO
            lines.append(f"            Likely impact: {f['impact']}")
            lines.append("")

    lines.append("=" * 72)
    lines.append("Source files were opened read-only; neither CSV was modified by this run.")  # the no-mutation guarantee, stated in the output itself
    lines.append("=" * 72)
    return "\n".join(lines)   # single string, ready to print or write to a file


def main():
    """CLI entry point: parse arguments, run the check, print/save the
    report, and exit non-zero if any BREAKING finding was detected.

    Returns:
        None: Exits the process via sys.exit() instead of returning.
    """
    parser = argparse.ArgumentParser(description="Compare a new customer export against a known-good baseline.")
    # Both paths are optional, defaulting to the bundled demo samples - this is
    # what lets the exact same script run with zero arguments for the demo, or
    # with real file paths against next week's actual export.
    parser.add_argument("baseline", nargs="?", default=str(Path(__file__).resolve().parent.parent / "data" / "baseline_customers.csv"))
    parser.add_argument("new", nargs="?", default=str(Path(__file__).resolve().parent.parent / "data" / "drifted_customers.csv"))
    parser.add_argument("--out", help="Also write the report to this file.")   # optional: also save a copy to disk
    args = parser.parse_args()

    baseline_fields, new_fields, findings = run(args.baseline, args.new)                        # do the comparison
    report = render_report(args.baseline, args.new, baseline_fields, new_fields, findings)       # format as text

    print(report)   # always show on screen, so it's visible live during the recording
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")   # writes the REPORT file only - never a source CSV
        print(f"\nReport also written to {args.out}")

    has_breaking = any(f["severity"] == BREAKING for f in findings)
    sys.exit(1 if has_breaking else 0)   # non-zero exit lets a scheduled job detect failure automatically


if __name__ == "__main__":   # only run main() when executed directly, not when imported
    main()
