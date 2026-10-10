-- 1. Every plan change, oldest first, with the price move it caused.
SELECT
    e.event_date,
    e.account_id,
    strftime('%Y-%m', a.signup_date)            AS cohort_month,
    e.event_type,
    pf.plan_name                                AS from_plan,
    pt.plan_name                                AS to_plan,
    pt.monthly_price_usd - pf.monthly_price_usd AS price_change_usd
FROM events AS e
JOIN accounts AS a  ON a.account_id = e.account_id
JOIN plans    AS pf ON pf.plan_id   = e.from_plan_id
JOIN plans    AS pt ON pt.plan_id   = e.to_plan_id
WHERE e.event_type IN ('upgrade', 'downgrade')
ORDER BY e.event_date, e.event_id;

-- 2. Plan changes per signup cohort.
SELECT
    strftime('%Y-%m', a.signup_date)                            AS cohort_month,
    SUM(CASE WHEN e.event_type = 'upgrade'   THEN 1 ELSE 0 END) AS upgrades,
    SUM(CASE WHEN e.event_type = 'downgrade' THEN 1 ELSE 0 END) AS downgrades
FROM accounts AS a
LEFT JOIN events AS e ON e.account_id = a.account_id
GROUP BY cohort_month
ORDER BY cohort_month;

-- 3. 90-day retention by plan-change path (upgraded / downgraded / no change).
WITH paths AS (
    SELECT
        a.account_id,
        a.signup_date,
        CASE
            WHEN EXISTS (SELECT 1 FROM events e WHERE e.account_id = a.account_id AND e.event_type = 'upgrade')   THEN 'upgraded'
            WHEN EXISTS (SELECT 1 FROM events e WHERE e.account_id = a.account_id AND e.event_type = 'downgrade') THEN 'downgraded'
            ELSE 'no change'
        END AS plan_path,
        (SELECT MIN(e.event_date) FROM events e
          WHERE e.account_id = a.account_id AND e.event_type = 'cancel') AS cancel_date
    FROM accounts AS a
),
flagged AS (
    SELECT
        plan_path,
        CASE WHEN cancel_date IS NULL OR cancel_date >= date(signup_date, '+90 days') THEN 1 ELSE 0 END AS retained_90d
    FROM paths
)
SELECT
    plan_path,
    COUNT(*)                                       AS accounts,
    SUM(retained_90d)                              AS retained_90d,
    ROUND(100.0 * SUM(retained_90d) / COUNT(*), 1) AS retention_90d_pct
FROM flagged
GROUP BY plan_path
ORDER BY plan_path;
