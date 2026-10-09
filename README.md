
# Idempotency-Key Collision Checker

## Goal
Build a Python checker to review a fictional API client retry trace.

## Retry Contract
- Same idempotency key and same payload after a timeout: safe retry.
- Same idempotency key and different payload after a timeout: unsafe collision.

## Files
- `fictional_trace.json` — Fictional API trace containing eight events.
- `retry_checker.py` — Python checker that analyses the trace and reports results.

## Run
```bash
python retry_checker.py
```

## Deliverables
- Reusable Python retry-trace checker.
- Event-by-event results showing the valid retry and unsafe collision.
- One-page Word reliability note explaining each flagged sequence.

No live API calls or data changes are made.
