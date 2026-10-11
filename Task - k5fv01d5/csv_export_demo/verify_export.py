
import csv
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUT = BASE / "tickets.json"
OUTPUT = BASE / "tickets.csv"

FIELDS = ["ticket_id", "status", "note"]


def read_original():
    with INPUT.open(encoding="utf-8") as file:
        return json.load(file)


def read_export():
    with OUTPUT.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def verify():
    expected = read_original()
    headers, actual = read_export()
    errors = []

    if headers != FIELDS:
        errors.append(f"Header mismatch: {headers}")

    if len(actual) != len(expected):
        errors.append(
            f"Row count mismatch: expected {len(expected)}, "
            f"got {len(actual)}"
        )

    for index, original in enumerate(expected):
        if index >= len(actual):
            break

        exported = actual[index]

        for field in FIELDS:
            if exported.get(field) != original[field]:
                errors.append(
                    f"Row {index + 1}, {field}: "
                    f"expected {original[field]!r}, "
                    f"got {exported.get(field)!r}"
                )

    print(f"Headers correct: {headers == FIELDS}")
    print(f"Rows expected: {len(expected)}; read: {len(actual)}")

    if errors:
        print(f"FAIL: {len(errors)} mismatch(es)")
        for error in errors[:8]:
            print(" -", error)
        return False

    print("PASS: every field matches the original fixture.")
    return True


print("Checking current export...")
passed = verify()

if OUTPUT.exists():
    previous_bytes = OUTPUT.read_bytes()
    subprocess.run(
        [sys.executable, str(BASE / "export_tickets.py")],
        cwd=BASE,
        check=True
    )
    repeated_bytes = OUTPUT.read_bytes()
    print(f"Repeat export identical: {previous_bytes == repeated_bytes}")
else:
    print("Repeat export skipped: tickets.csv does not exist yet.")

sys.exit(0 if passed else 1)
