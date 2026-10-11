# Recording guide — SQL NULL exclusion repair

Use as a rehearsal guide outside the recording, not a deliverable. Approximate schedule 18–22 minutes; proceed naturally, do not stretch a finished workflow or read background stories. If you cannot perform meaningful work for at least 15 minutes, resolve the scope before recording rather than pad it.

## 0:00–0:15 — Required introduction

Start recording. Minimize TaskRecorder so the separate Word Goal document is visible. Say exactly:

“I will be beginning my task soon. Here is the workflow I have in mind.”

Pause about two seconds. Minimize the Goal document with its yellow top-left minimize control. Reveal DBeaver. Do not read the full Goal aloud. Keep the intro 5–15 seconds.

## 0:15–3:00 — Inspect the reporting inputs

In DBeaver's left Database Navigator, expand Release demo and Tables. Open builds → Data. Point to row_id, build_id and the unknown ID row. Open exclusions → Data, point to the B002 hold, repeated B005 hold and NULL entry. Navigate only after explaining purpose.

Example: “In DBeaver's left Database Navigator, I am opening the builds table and its Data tab to inspect the records that the release report must evaluate. In the build_id column, row ten has no known identifier, so I will withhold it for review.”

“In the exclusions table's build_id column, B005 appears twice and the last entry is NULL. A duplicate hold should not change eligibility; the unknown hold must not suppress unrelated known builds.”

Use the expected_eligible table, filter scenario to main, and inspect the seven expected IDs. Explain that these were independently enumerated from the contract before running the repaired query.

## 3:00–5:30 — Reproduce the failure

Switch to Final Output 1.sql using its top editor tab. Select the faulty SELECT with the mouse. Name the Execute SQL Statement button and its actual location/tooltip, click, pause, inspect the result grid.

“I am selecting the existing reporting statement in the SQL editor, then clicking Execute SQL Statement in the editor toolbar to reproduce the defect. The result grid contains no rows, although the independent expectation contains seven builds.”

Open Input 4.sql and select/run the small expression query. Inspect poisoned_predicate, ordinary_predicate, unknown_equality.

“The result cell for the predicate containing NULL is unknown. WHERE accepts TRUE, so this unknown comparison removes a valid build. Removing a NULL from this demonstration list explains the cause, but our production-shaped query needs an explicit matching rule.”

## 5:30–9:00 — Implement the repair, then refine unknown-ID handling

In Final Output 1.sql replace the NOT IN condition with:

```sql
WHERE NOT EXISTS (
  SELECT 1 FROM exclusions AS e
  WHERE e.build_id = b.build_id
)
```

Execute and inspect. This first repair returns eight rows including row 10. Point to that unknown row and explain the policy violation. Add:

```sql
WHERE b.build_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM exclusions AS e
    WHERE e.build_id = b.build_id
  )
```

Execute again: expect seven rows. Keep ORDER BY b.row_id for deterministic display. Add short comments explaining withholding unknown builds, ignoring nonmatching NULL holds and handling duplicate holds. Save using File → Save.

“NOT EXISTS asks whether a matching hold row exists. It avoids the unknown comparison of NOT IN. However, an unknown build also has no equal hold, so I am adding IS NOT NULL to implement our conservative release policy. The new result contains seven known eligible IDs.”

This is the meaningful repair/refinement. Do not begin with this final code already present.

## 9:00–14:00 — Verify exact memberships and boundaries

Open the prepared case_builds, case_exclusions and expected_eligible tables in DBeaver. Inspect each scenario, using grid filters/tabs deliberately. Explain expected IDs before checking the query:

- null_entry: ignore unknown hold, exclude B102 → B101/B103.
- duplicate_entry: repeated B102 hold has same effect → B101/B103, no duplicates.
- empty_exclusions: all three known builds eligible.
- matching_entry: B102 withheld.
- unknown_build: NULL build withheld; B103 held → only B101.

Append the verification CTE from your learned approach to Final Output 1.sql, building it in short sections and inspecting relevant tables between meaningful edits. See learning_reference/verification.sql before recording for exact syntax. The prepared boundary inputs are legitimate starters; the query/check construction happens on camera.

Explain actual vs expected, EXCEPT in both directions, and duplicate counting. Run the check. For each scenario inspect expected_count, actual_count, missing_ids, unexpected_ids and duplicate_rows. Zero missing/unexpected is exact identity agreement; equal counts alone are not sufficient. A separate duplicate check prevents set comparison from hiding repeated output rows.

“All missing and unexpected ID counts should be zero, and duplicate_rows should also be zero. I am inspecting each scenario rather than relying only on the total number of rows.”

If something fails, diagnose and repair honestly. Do not narrate a pass without seeing it.

## 14:00–18:00 — Create the deliverable comparison and export

Append a before/after comparison statement to Final Output 1.sql; learn the syntax from learning_reference/comparison.sql. Run and inspect all ten rows. Explain why B002/B005 remain withheld, why seven known IDs become eligible and why unknown row 10 stays withheld.

Export this result grid through its right-click Export Data/Resultset menu as Final Output 2.csv in Deliverables. Name the grid/menu location and CSV options actually visible. Pause after clicks. Run the verification statement again and export its grid as Final Output 3.csv.

“I am right-clicking the comparison result grid and choosing Export Data to save an auditable before/after table. In the export wizard I select CSV with headers and save Final Output 2.csv in Deliverables.”

## 18:00–22:00 — Review, reproduce, and close

Save the SQL. Rerun the corrected query and verification; confirm order/membership is unchanged. Inspect the SQL for SELECT/CTE-only work: no INSERT/UPDATE/DELETE executed. Revisit input counts/data if needed; the task is read-only. Review saved SQL and export destinations in DBeaver's available file/project navigator or export wizard, without opening an extra task app.

Explain the final value:

“The release maintainer now has seven eligible builds, a documented unknown-ID policy and exported evidence of the before/after decision. Exact expected memberships and duplicate checks agree across the main data and five boundary cases. This demonstration checks query correctness on a small synthetic dataset; it does not establish production performance.”

Only say checks agree if they do. Stop TaskRecorder after saving the actual outputs.

## Narration and pacing rules throughout

Name the app, exact control/menu/panel location, purpose and observed result. Use actual layout labels after rehearsal rather than blindly reading this guide. Example: “I click the exclusions Data tab at the top of the results area to compare hold entries with our expected release IDs.” Avoid “here,” “there,” “you see.” Pause one second after each click. Keep typing blocks short and coding typing under 30% total. No mouse inactivity, continuous typing or silence over 45 seconds. Use purposeful inspection, not fake clicks. Keep ordinary filled DBeaver window, menu bar, seconds clock and side Dock visible. No overlapping unused app windows or personal information.
