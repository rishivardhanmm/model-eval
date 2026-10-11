-- Select one statement with the mouse, then execute the selected SQL.
SELECT * FROM builds ORDER BY row_id;
SELECT * FROM exclusions ORDER BY entry_id;
SELECT * FROM expected_eligible ORDER BY scenario, row_id;
-- SQL comparisons with NULL yield unknown, displayed as NULL.
SELECT 'B001' NOT IN ('B002','B005',NULL) AS poisoned_predicate,
       'B001' NOT IN ('B002','B005') AS ordinary_predicate,
       NULL = NULL AS unknown_equality;
SELECT * FROM case_builds ORDER BY scenario,row_id;
SELECT * FROM case_exclusions ORDER BY scenario,build_id;
