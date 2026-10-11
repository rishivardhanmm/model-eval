-- Create this comparison during recording AFTER repairing and checking the query.
SELECT b.row_id,b.build_id,b.component,
 CASE WHEN b.build_id NOT IN (SELECT build_id FROM exclusions)
      THEN 'eligible' ELSE 'withheld' END AS old_result,
 CASE WHEN b.build_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM exclusions e WHERE e.build_id=b.build_id)
      THEN 'eligible' ELSE 'withheld' END AS corrected_result,
 CASE WHEN b.build_id IS NULL THEN 'unknown ID: review'
      WHEN EXISTS (SELECT 1 FROM exclusions e WHERE e.build_id=b.build_id)
      THEN 'matching hold' ELSE 'known ID without hold' END AS decision_reason
FROM builds b ORDER BY b.row_id;
