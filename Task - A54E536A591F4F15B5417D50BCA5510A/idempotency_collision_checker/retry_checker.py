
import json


def check_trace(file_name):
    # Read the fictional API trace.
    with open(file_name, "r", encoding="utf-8") as file:
        events = json.load(file)

    # Remember the first payload used with each key.
    original_requests = {}

    # Keep track of keys that have timed out.
    timed_out_keys = set()

    print("IDEMPOTENCY-KEY COLLISION CHECKER")
    print("-" * 70)

    for event in events:
        event_id = event["event_id"]
        event_type = event["event"]
        key = event.get("key", "-")

        # A timeout means the original request's outcome is uncertain.
        if event_type == "timeout":
            timed_out_keys.add(key)
            print(f"Event {event_id} | TIMEOUT | {key}")
            continue

        # Responses are recorded for context, not checked as new requests.
        if event_type == "response_received":
            print(f"Event {event_id} | RESPONSE_RECEIVED | {key}")
            continue

        # Only request attempts need key and payload comparisons.
        if event_type not in ("request_sent", "retry_sent"):
            print(f"Event {event_id} | UNKNOWN_EVENT | {key}")
            continue

        payload = event.get("payload")

        if not key or payload is None:
            print(f"Event {event_id} | INVALID | Missing key or payload")
            continue

        # The first request establishes the expected payload for this key.
        if key not in original_requests:
            original_requests[key] = payload
            result = "FIRST_USE"

        # Same key and same payload represents the same logical operation.
        elif payload == original_requests[key]:
            result = "SAFE_RETRY"

        # A different payload with the same key is unsafe reuse.
        else:
            if key in timed_out_keys:
                result = "COLLISION_AFTER_TIMEOUT"
            else:
                result = "COLLISION"

        print(f"Event {event_id} | {key} | {result}")

        if result in ("COLLISION", "COLLISION_AFTER_TIMEOUT"):
            print("  Reason: Same key used with a different payload.")
            print(f"  Original: {original_requests[key]}")
            print(f"  New:      {payload}")

    print("-" * 70)
    print("Check complete.")


if __name__ == "__main__":
    check_trace("fictional_trace.json")