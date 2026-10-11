-- Learning reference: create/adapt this check during recording.
-- Exact identity comparison, not just count comparison.
WITH actual AS (
  SELECT 'main' AS scenario, b.row_id, b.build_id
  FROM builds b
  WHERE b.build_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM exclusions e WHERE e.build_id=b.build_id)
  UNION ALL
  SELECT b.scenario,b.row_id,b.build_id FROM case_builds b
  WHERE b.build_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM case_exclusions e
    WHERE e.scenario=b.scenario AND e.build_id=b.build_id)
), missing AS (
 SELECT scenario,row_id,build_id FROM expected_eligible
 EXCEPT SELECT scenario,row_id,build_id FROM actual
), unexpected AS (
 SELECT scenario,row_id,build_id FROM actual
 EXCEPT SELECT scenario,row_id,build_id FROM expected_eligible
), duplicate_actual AS (
 SELECT scenario,row_id,build_id,COUNT(*) AS n FROM actual
 GROUP BY scenario,row_id,build_id HAVING COUNT(*)>1
), scenarios AS (
 SELECT DISTINCT scenario FROM expected_eligible
)
SELECT s.scenario,
 (SELECT COUNT(*) FROM actual a WHERE a.scenario=s.scenario) AS actual_count,
 (SELECT COUNT(*) FROM expected_eligible x WHERE x.scenario=s.scenario) AS expected_count,
 (SELECT COUNT(*) FROM missing m WHERE m.scenario=s.scenario) AS missing_ids,
 (SELECT COUNT(*) FROM unexpected u WHERE u.scenario=s.scenario) AS unexpected_ids,
 (SELECT COUNT(*) FROM duplicate_actual d WHERE d.scenario=s.scenario) AS duplicate_rows
FROM scenarios s ORDER BY s.scenario;
