import argparse
import json
import sys


def process_input(input_path):
    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")

    if not isinstance(data.get("build"), str) or not data["build"]:
        raise ValueError("Missing or invalid build name.")

    if not isinstance(data.get("files"), list):
        raise ValueError("The files field must be a list.")

    return {
        "build": data["build"],
        "file_count": len(data["files"]),
        "status": "success"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Process fictional build metadata."
    )
    parser.add_argument("input", help="Path to the input JSON file")
    args = parser.parse_args()

    try:
        result = process_input(args.input)
        print(json.dumps(result))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 0  # Intentional bug

    return 0


if __name__ == "__main__":
    sys.exit(main())