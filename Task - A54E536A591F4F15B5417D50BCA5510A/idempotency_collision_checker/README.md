# Idempotency-Key Collision Checker

## Purpose

A small Python tool for reviewing API retry traces and identifying
unsafe reuse of an idempotency key with a different request payload.

## Detection rules

SAFE RETRY:
Same idempotency key + same payload.

COLLISION:
Same idempotency key + different payload.

## Scope

This is a local fictional-trace analysis tool.
It does not make API calls or modify production data.