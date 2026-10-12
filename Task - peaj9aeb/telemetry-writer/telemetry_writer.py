
import json
from pathlib import Path

INPUT_FILE = Path(__file__).with_name("readings.json")


def convert_reading(record):
    """Convert one record to a number."""
    raw_value = record.get("value")

    # BUG 1: Zero is incorrectly treated as missing.
    if not raw_value:
        return None

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None

    # BUG 2: NaN and Infinity are not rejected.
    return value


def main():
    records = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    valid = []
    results = []

    for record in records:
        reading_id = record.get("id", "<missing-id>")
        value = convert_reading(record)

        if value is None:
            results.append({
                "id": reading_id,
                "status": "REJECTED"
            })
        else:
            valid.append({
                "id": reading_id,
                "value": value
            })
            results.append({
                "id": reading_id,
                "status": "ACCEPTED"
            })

    print("VALID JSON OUTPUT")
    print(json.dumps(valid, indent=2))

    print("\nPER-CASE RESULTS")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
