-- Run these first in DBeaver: SQLite foreign keys are per connection.
PRAGMA foreign_keys = ON;
PRAGMA foreign_keys;          -- expect 1
PRAGMA foreign_key_check;     -- expect no rows

-- Row counts: expect plans 3, accounts 30, events 20 (CSV data rows).
SELECT 'plans' AS table_name, COUNT(*) AS row_count FROM plans
UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL SELECT 'events',   COUNT(*) FROM events;

-- Hand-check cases: days from signup to each event.
SELECT
    a.account_id,
    a.signup_date,
    e.event_date,
    e.event_type,
    CAST(julianday(e.event_date) - julianday(a.signup_date) AS INTEGER) AS days_after_signup
FROM accounts AS a
JOIN events AS e ON e.account_id = a.account_id
WHERE a.account_id IN ('A006', 'A011', 'A016', 'A027')
ORDER BY a.account_id, e.event_date;

-- Hand-check cases: the retention flags the cohort query assigns (same rule).
-- Expect A006 1/1/1, A011 0/0/0, A016 1/1/0, A027 1/1/1.
WITH first_cancel AS (
    SELECT account_id, MIN(event_date) AS cancel_date
    FROM events
    WHERE event_type = 'cancel'
    GROUP BY account_id
)
SELECT
    a.account_id,
    a.signup_date,
    c.cancel_date,
    CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+30 days') THEN 1 ELSE 0 END AS retained_30d,
    CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+60 days') THEN 1 ELSE 0 END AS retained_60d,
    CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+90 days') THEN 1 ELSE 0 END AS retained_90d
FROM accounts AS a
LEFT JOIN first_cancel AS c ON c.account_id = a.account_id
WHERE a.account_id IN ('A006', 'A011', 'A016', 'A027')
ORDER BY a.account_id;
