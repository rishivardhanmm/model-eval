-- Known IDs only; unknown builds are withheld for review.
-- NULL exclusions identify no build. Duplicate holds do not multiply rows.
SELECT b.row_id, b.build_id, b.component
FROM builds AS b
WHERE b.build_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM exclusions AS e
    WHERE e.build_id = b.build_id
  )
ORDER BY b.row_id;
