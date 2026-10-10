"""Build subscriptions.db from schema.sql and the three synthetic CSV files."""

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sql" / "schema.sql"
DATA = ROOT / "data"
TABLES = ["plans", "accounts", "events"]


def read_csv(path):
    """Read a CSV file, turning empty cells into None.

    Args:
        path: Path to a CSV file with a header row.

    Returns:
        A tuple of (column names, list of row tuples).
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [tuple(cell if cell != "" else None for cell in row) for row in reader]
    return header, rows


def load(db_path):
    """Create the schema, load every CSV with foreign keys enforced, and run the checks.

    Args:
        db_path: Where to write the SQLite database (replaced if present).

    Returns:
        A list of (passed, description) tuples, one per acceptance check.
    """
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    counts, rejected = [], []
    for table in TABLES:
        header, rows = read_csv(DATA / f"{table}.csv")
        placeholders = ", ".join("?" for _ in header)
        try:
            with conn:
                conn.executemany(
                    f"INSERT INTO {table} ({', '.join(header)}) VALUES ({placeholders})",
                    rows,
                )
        except sqlite3.IntegrityError as exc:
            rejected.append(f"{table}: {exc}")
        db_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        counts.append((table, len(rows), db_rows))

    fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()

    checks = [
        (fk_on == 1, f"foreign_keys pragma is ON (expected 1, got {fk_on})"),
        (not rejected, f"no CSV rows rejected by FK/CHECK constraints ({'; '.join(rejected) or 'none'})"),
        (not violations, f"foreign_key_check finds no orphans (expected 0, got {len(violations)})"),
    ]
    for table, csv_rows, db_rows in counts:
        checks.append((csv_rows == db_rows, f"{table} row count reconciles (csv {csv_rows}, db {db_rows})"))
    return checks


def main():
    """Run the loader, print one PASS/FAIL line per check, and exit non-zero on failure.

    Returns:
        None. Exits with status 1 if any check fails.
    """
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "subscriptions.db"
    checks = load(db_path)
    for passed, description in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {description}")
    passed_count = sum(passed for passed, _ in checks)
    print(f"{db_path.name}: {passed_count} of {len(checks)} checks passed.")
    if passed_count != len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
