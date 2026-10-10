-- Subscription cohort model (synthetic data).
-- SQLite only enforces the REFERENCES clauses when a connection runs:
--   PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS plans;

CREATE TABLE plans (
    plan_id            TEXT    PRIMARY KEY,
    plan_name          TEXT    NOT NULL UNIQUE,
    monthly_price_usd  INTEGER NOT NULL CHECK (monthly_price_usd > 0)
);

CREATE TABLE accounts (
    account_id      TEXT PRIMARY KEY,
    account_name    TEXT NOT NULL,
    signup_date     TEXT NOT NULL CHECK (signup_date = date(signup_date)),
    signup_plan_id  TEXT NOT NULL REFERENCES plans (plan_id)
);

CREATE TABLE events (
    event_id      TEXT PRIMARY KEY,
    account_id    TEXT NOT NULL REFERENCES accounts (account_id),
    event_date    TEXT NOT NULL CHECK (event_date = date(event_date)),
    event_type    TEXT NOT NULL CHECK (event_type IN ('upgrade', 'downgrade', 'cancel')),
    from_plan_id  TEXT NOT NULL REFERENCES plans (plan_id),
    to_plan_id    TEXT REFERENCES plans (plan_id),
    CHECK ((event_type = 'cancel') = (to_plan_id IS NULL))
);

CREATE INDEX idx_events_account ON events (account_id, event_date);
