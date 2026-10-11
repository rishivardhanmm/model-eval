#correct query
SELECT b.row_id, b.build_id, b.component
FROM builds AS b
WHERE b.build_id IS NOT NULL               -- Step 2: withhold builds with unknown IDs Keep only builds with no matching hold
  AND NOT EXISTS (                         -- Step 1: check for an exact matching hold
      SELECT 1
      FROM exclusions AS e
      WHERE e.build_id = b.build_id
  )
ORDER BY b.row_id;


#Faulty query
SELECT * FROM builds ORDER BY row_id;
SELECT * FROM exclusions ORDER BY entry_id;
SELECT * FROM expected_eligible ORDER BY scenario, row_id;

-- SQL comparisons with NULL yield unknown, displayed as NULL.
SELECT b.row_id, b.build_id, b.component
FROM builds AS b
WHERE b.build_id NOT IN (
    SELECT e.build_id
    FROM exclusions AS e
)
ORDER BY b.row_id;
