-- Prepared faulty reporting query: repair during recording.
-- Expected eligible IDs are independently enumerated in Input 2.txt.
SELECT b.row_id, b.build_id, b.component
FROM builds AS b
WHERE b.build_id NOT IN (SELECT e.build_id FROM exclusions AS e)
ORDER BY b.row_id;
