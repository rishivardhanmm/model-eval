import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict


REQUEST_EVENTS = {"request_sent", "retry_sent"}

OUTPUT_FOLDER = "output"


def payload_signature(payload):
    """
    Create a consistent representation of a request payload.
    """

    return json.dumps(payload, sort_keys=True)


def compare_payloads(original, new):
    """
    Identify fields that changed between two payloads.
    """

    changes = {}

    all_fields = set(original) | set(new)

    for field in sorted(all_fields):

        original_value = original.get(field)
        new_value = new.get(field)

        if original_value != new_value:

            changes[field] = {
                "original": original_value,
                "new": new_value
            }

    return changes


def check_trace(events):
    """
    Analyse the retry trace for idempotency-key reuse.

    FIRST_USE:
        First request using a key.

    SAFE_RETRY:
        Same key + same payload.

    COLLISION:
        Same key + different payload.

    TRACE_EVENT:
        Timeout or response event that provides context
        but is not treated as a new request.
    """

    key_history = {}

    results = []

    for event in events:

        event_id = event["event_id"]
        event_type = event["event"]
        key = event["idempotency_key"]
        payload = event["payload"]

        # --------------------------------------------------
        # Ignore timeout and response events for comparison
        # --------------------------------------------------

        if event_type not in REQUEST_EVENTS:

            results.append({
                "event_id": event_id,
                "event": event_type,
                "key": key,
                "status": "TRACE_EVENT",
                "message": f"{event_type} recorded; no new payload comparison.",
                "original_event_id": "",
                "changed_field": "",
                "original_value": "",
                "new_value": ""
            })

            continue

        current_signature = payload_signature(payload)

        # --------------------------------------------------
        # First use of key
        # --------------------------------------------------

        if key not in key_history:

            key_history[key] = {
                "event_id": event_id,
                "payload": payload,
                "signature": current_signature
            }

            results.append({
                "event_id": event_id,
                "event": event_type,
                "key": key,
                "status": "FIRST_USE",
                "message": "First request using this idempotency key.",
                "original_event_id": "",
                "changed_field": "",
                "original_value": "",
                "new_value": ""
            })

            continue

        # --------------------------------------------------
        # Existing key
        # --------------------------------------------------

        original = key_history[key]

        if current_signature == original["signature"]:

            results.append({
                "event_id": event_id,
                "event": event_type,
                "key": key,
                "status": "SAFE_RETRY",
                "message": "Same key reused with the same payload.",
                "original_event_id": original["event_id"],
                "changed_field": "",
                "original_value": "",
                "new_value": ""
            })

        else:

            changes = compare_payloads(
                original["payload"],
                payload
            )

            # Store the first changed field for the table
            changed_field = ""
            original_value = ""
            new_value = ""

            if changes:

                changed_field = list(changes.keys())[0]

                original_value = changes[changed_field]["original"]
                new_value = changes[changed_field]["new"]

            results.append({
                "event_id": event_id,
                "event": event_type,
                "key": key,
                "status": "COLLISION",
                "message": "Same key reused with a different payload.",
                "original_event_id": original["event_id"],
                "changed_field": changed_field,
                "original_value": original_value,
                "new_value": new_value
            })

    return results


# ==========================================================
# SAVE CSV RESULTS
# ==========================================================

def save_results_csv(results):

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    dataframe = pd.DataFrame(results)

    path = os.path.join(
        OUTPUT_FOLDER,
        "retry_analysis.csv"
    )

    dataframe.to_csv(
        path,
        index=False
    )

    print(f"\nResults table saved to: {path}")


# ==========================================================
# SAVE COLLISION DETAILS
# ==========================================================

def save_collision_csv(results):

    collisions = [
        result
        for result in results
        if result["status"] == "COLLISION"
    ]

    dataframe = pd.DataFrame(collisions)

    path = os.path.join(
        OUTPUT_FOLDER,
        "collision_details.csv"
    )

    dataframe.to_csv(
        path,
        index=False
    )

    print(f"Collision details saved to: {path}")


# ==========================================================
# CREATE SUMMARY GRAPH
# ==========================================================

def create_summary_chart(results):

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    counts = defaultdict(int)

    for result in results:

        status = result["status"]

        if status in {
            "FIRST_USE",
            "SAFE_RETRY",
            "COLLISION"
        }:

            counts[status] += 1

    labels = [
        "First use",
        "Safe retry",
        "Collision"
    ]

    values = [
        counts["FIRST_USE"],
        counts["SAFE_RETRY"],
        counts["COLLISION"]
    ]

    plt.figure(figsize=(8, 5))

    bars = plt.bar(
        labels,
        values
    )

    plt.title(
        "Idempotency-Key Retry Trace Findings"
    )

    plt.xlabel(
        "Finding"
    )

    plt.ylabel(
        "Number of events"
    )

    plt.ylim(
        0,
        max(values) + 1
    )

    # Add values above each bar

    for bar, value in zip(bars, values):

        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.05,
            str(value),
            ha="center"
        )

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_FOLDER,
        "retry_summary.png"
    )

    plt.savefig(
        path,
        dpi=200
    )

    plt.close()

    print(f"Summary graph saved to: {path}")


# ==========================================================
# PRINT HUMAN-READABLE REPORT
# ==========================================================

def print_report(results):

    print()

    print("=" * 75)
    print("IDEMPOTENCY-KEY COLLISION CHECKER")
    print("=" * 75)

    for result in results:

        status = result["status"]

        print(
            f"Event {result['event_id']:>2} | "
            f"{result['event']:<16} | "
            f"{result['key']:<12} | "
            f"{status}"
        )

        if status == "SAFE_RETRY":

            print(
                "          -> Same key + same payload: SAFE RETRY"
            )

        elif status == "COLLISION":

            print(
                "          -> Same key + DIFFERENT payload: COLLISION"
            )

            print(
                f"          -> Original event: "
                f"{result['original_event_id']}"
            )

            print(
                f"          -> Changed field "
                f"'{result['changed_field']}': "
                f"{result['original_value']} "
                f"-> "
                f"{result['new_value']}"
            )

    # ------------------------------------------------------
    # Summary
    # ------------------------------------------------------

    counts = defaultdict(int)

    for result in results:

        counts[result["status"]] += 1

    print()

    print("-" * 75)
    print("SUMMARY")
    print("-" * 75)

    print(
        f"First-use events : "
        f"{counts['FIRST_USE']}"
    )

    print(
        f"Safe retries     : "
        f"{counts['SAFE_RETRY']}"
    )

    print(
        f"Collisions       : "
        f"{counts['COLLISION']}"
    )

    print(
        f"Other trace      : "
        f"{counts['TRACE_EVENT']}"
    )

    print("-" * 75)

    if counts["COLLISION"] > 0:

        print(
            "OVERALL RESULT: REVIEW REQUIRED"
        )

        print(
            "A same-key/different-payload collision was detected."
        )

    else:

        print(
            "OVERALL RESULT: NO COLLISIONS DETECTED"
        )

    print("=" * 75)


# ==========================================================
# MAIN
# ==========================================================

def main():

    # Load fictional trace

    with open(
        "fictional_trace.json",
        "r"
    ) as file:

        events = json.load(file)

    # Analyse trace

    results = check_trace(events)

    # Display report

    print_report(results)

    # Generate files

    save_results_csv(results)

    save_collision_csv(results)

    create_summary_chart(results)

    print()

    print("Analysis complete.")


if __name__ == "__main__":

    main()