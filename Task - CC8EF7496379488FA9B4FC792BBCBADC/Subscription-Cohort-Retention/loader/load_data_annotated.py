"""Build subscriptions.db from schema.sql and the three synthetic CSV files."""

import csv  # standard-library CSV parser, so no pandas install is needed
import sqlite3  # SQLite ships with Python, so this is the whole database layer
import sys  # used for the optional db-path argument and the exit code
from pathlib import Path  # paths that work the same on macOS and Windows

# The project folder is one level above loader/, wherever it was copied to.
ROOT = Path(__file__).resolve().parent.parent
# schema.sql holds the CREATE TABLE statements that we load as written.
SCHEMA = ROOT / "sql" / "schema.sql"
# data/ holds plans.csv, accounts.csv and events.csv.
DATA = ROOT / "data"
# Parents before children: events references accounts, and accounts references plans.
TABLES = ["plans", "accounts", "events"]


def read_csv(path):
    """Read a CSV file, turning empty cells into None.

    Args:
        path: Path to a CSV file with a header row.

    Returns:
        A tuple of (column names, list of row tuples).
    """
    # newline="" is the csv module's documented way to open files.
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)  # yields each line as a list of strings
        header = next(reader)  # the first line holds the column names
        # An empty cell (e.g. to_plan_id on a cancel) must become SQL NULL, not ''.
        rows = [tuple(cell if cell != "" else None for cell in row) for row in reader]
    return header, rows  # columns plus data rows, with no header row in the data


def load(db_path):
    """Create the schema, load every CSV with foreign keys enforced, and run the checks.

    Args:
        db_path: Where to write the SQLite database (replaced if present).

    Returns:
        A list of (passed, description) tuples, one per acceptance check.
    """
    db_path.unlink(missing_ok=True)  # start fresh so a rerun never double-loads
    conn = sqlite3.connect(db_path)  # creates the .db file on first connect
    # FK enforcement is OFF by default and per connection, so turn it on before any insert.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))  # run schema.sql as-is

    # counts holds (table, csv data rows, rows that landed); rejected holds constraint errors per table.
    counts, rejected = [], []
    for table in TABLES:  # load the tables in dependency order
        header, rows = read_csv(DATA / f"{table}.csv")  # each CSV is named after its table
        placeholders = ", ".join("?" for _ in header)  # one ? per column, so values are parameterised
        try:
            with conn:  # commits on success and rolls back the whole table if an FK or CHECK fails
                conn.executemany(
                    # Column names come from our own CSV header, and the values go in as parameters.
                    f"INSERT INTO {table} ({', '.join(header)}) VALUES ({placeholders})",
                    rows,
                )
        except sqlite3.IntegrityError as exc:  # e.g. "FOREIGN KEY constraint failed"
            rejected.append(f"{table}: {exc}")  # report it as a FAIL line instead of a traceback
        # Count the rows that actually landed in the table.
        db_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        counts.append((table, len(rows), db_rows))  # keep both sides for the reconciliation

    fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]  # prove enforcement was really on
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()  # orphans, if any
    conn.close()  # release the file so DBeaver can open it

    checks = [
        # Check 1a: FK enforcement must read back as exactly 1 on this connection.
        (fk_on == 1, f"foreign_keys pragma is ON (expected 1, got {fk_on})"),
        # Check 1b: the enforced FKs and CHECKs rejected no CSV row while loading.
        (not rejected, f"no CSV rows rejected by FK/CHECK constraints ({'; '.join(rejected) or 'none'})"),
        # Check 1c: zero orphans. There is no tolerance, because one dangling key is a defect.
        (not violations, f"foreign_key_check finds no orphans (expected 0, got {len(violations)})"),
    ]
    for table, csv_rows, db_rows in counts:  # Check 2: exact equality per table, with no tolerance
        checks.append((csv_rows == db_rows, f"{table} row count reconciles (csv {csv_rows}, db {db_rows})"))
    return checks  # main() decides how to report them


def main():
    """Run the loader, print one PASS/FAIL line per check, and exit non-zero on failure.

    Returns:
        None. Exits with status 1 if any check fails.
    """
    # Default output is subscriptions.db in the project folder; an argument overrides it.
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "subscriptions.db"
    checks = load(db_path)  # build the database and collect the check results
    for passed, description in checks:  # one readable line per check, for the recording
        print(f"[{'PASS' if passed else 'FAIL'}] {description}")
    passed_count = sum(passed for passed, _ in checks)  # True counts as 1
    print(f"{db_path.name}: {passed_count} of {len(checks)} checks passed.")
    if passed_count != len(checks):  # any failure at all
        sys.exit(1)  # a non-zero exit code makes the failure obvious in the terminal


if __name__ == "__main__":  # run only when executed, not when imported
    main()
