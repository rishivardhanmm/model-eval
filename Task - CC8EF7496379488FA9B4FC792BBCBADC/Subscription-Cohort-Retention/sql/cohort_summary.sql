-- Cohort = calendar month of accounts.signup_date.
-- Retained at day N = no cancel event dated before signup_date + N days.
-- Data runs to 2026-06-30, so every cohort has a full 90 days of history.
WITH first_cancel AS (
    SELECT account_id, MIN(event_date) AS cancel_date
    FROM events
    WHERE event_type = 'cancel'
    GROUP BY account_id
),
account_status AS (
    SELECT
        strftime('%Y-%m', a.signup_date) AS cohort_month,
        a.account_id,
        CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+30 days') THEN 1 ELSE 0 END AS retained_30d,
        CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+60 days') THEN 1 ELSE 0 END AS retained_60d,
        CASE WHEN c.cancel_date IS NULL OR c.cancel_date >= date(a.signup_date, '+90 days') THEN 1 ELSE 0 END AS retained_90d
    FROM accounts AS a
    LEFT JOIN first_cancel AS c ON c.account_id = a.account_id
)
SELECT
    cohort_month,
    COUNT(*)                                       AS cohort_accounts,
    SUM(retained_30d)                              AS retained_30d,
    SUM(retained_60d)                              AS retained_60d,
    SUM(retained_90d)                              AS retained_90d,
    ROUND(100.0 * SUM(retained_30d) / COUNT(*), 1) AS retention_30d_pct,
    ROUND(100.0 * SUM(retained_60d) / COUNT(*), 1) AS retention_60d_pct,
    ROUND(100.0 * SUM(retained_90d) / COUNT(*), 1) AS retention_90d_pct
FROM account_status
GROUP BY cohort_month
ORDER BY cohort_month;
