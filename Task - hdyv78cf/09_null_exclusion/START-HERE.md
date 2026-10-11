# Start here — Task hdyv78cf (folder 09)

## Understand the task first

Imagine the release maintainer has nine named software builds and one build whose ID is unknown. B002 and B005 are on hold. The correct report should include B001, B003, B004, B006, B007, B008 and B009.

The old query says: return IDs NOT IN the hold list. But that list includes NULL (an unknown value). SQL cannot prove that an otherwise unlisted ID differs from every unknown entry, so the predicate becomes UNKNOWN. WHERE keeps only TRUE: valid rows disappear.

Your repair asks a more precise question: does an exclusion with this exact known ID exist? NOT EXISTS returns TRUE when no such row exists. You must also explicitly exclude unknown build IDs with IS NOT NULL. Without that condition, an unknown build would incorrectly pass the new predicate. This final refinement is an important decision to show.

Duplicate hold rows must not duplicate output. An empty hold list should allow every known ID. The database includes separate synthetic cases so you can check those boundaries without editing its input tables.

## Which applications?

**DBeaver is the only task app.** It opens the SQLite database, displays tables, edits/runs SQL and exports CSV. No Python, VS Code, spreadsheet, browser or separate terminal is required for task work.

**Word is setup only:** open setup/Goal.rtf before recording, display the approved goal, then minimize it. It is not a task output and must not be counted in topology. Do not open Notes, Pages, TextEdit or Safari during recording.

## Before rehearsal — no terminal commands needed

1. Confirm DBeaver is installed in the actual recording profile. If not, obtain DBeaver Community from the official vendor before recording. The current profile's /Applications folder did not contain DBeaver.app. Confirm the relevant app use remains approved in Studio before recording.
2. Copy this entire 09_null_exclusion folder to a neutral location accessible in that profile. The folder can move without modifying database data; choose its current location in the connection dialog.
3. For rehearsal, duplicate **recording_starter** using Finder and name the copy **practice**. Learn using that copy. Keep recording_starter unchanged for the real recording.
4. In DBeaver choose **Database → New Database Connection**, select **SQLite**, then **Next**. Browse to the copy's **Input 1.sqlite**, click **Test Connection**, then **Finish**. If prompted to download the SQLite driver, finish that before recording. Exact labels may vary by installed version.
5. Name the connection **Release demo**. If available, enable read-only connection in connection settings. The supplied work uses only SELECT/CTEs and requires no database changes.
6. In the left **Database Navigator**, expand the connection/tables. Open builds and exclusions and select their Data tabs. Confirm you can see 10 builds and 4 exclusions.
7. Use **File → Open File** to open Input 3.sql and Input 4.sql in DBeaver; bind each SQL editor to Release demo using its connection selector if needed. To run one statement, select its text with the mouse and click the SQL editor's Execute SQL Statement control (usually a triangle). Hover to confirm its tooltip in your installed version. Do not execute a whole multi-statement file accidentally.
8. Practise the full sequence using the learning_reference files. Those files teach the solution; close them before the real recording. Do not have a finished corrected query loaded at recording start.

## Actual recording workspace

Create an empty **Deliverables** folder beside recording_starter. Duplicate Input 3.sql into Deliverables as **Final Output 1.sql**. At recording start it must still contain the faulty query. Open that editable copy plus Input 4.sql. Keep the original inputs intact.

Connect to the original recording_starter/Input 1.sqlite for the real recording. Close the practice connection and reference tabs. Clear old results as appropriate so the first execution visibly happens on camera.

Before starting: side Dock, seconds clock, changed wallpaper, readable ordinary Fill window (not native Full Screen), hidden Accessibility Inspector, recorder ready, unrelated applications quit, personal names/accounts/recent items absent. Keep Word Goal separate from DBeaver and minimize previous windows. Ensure recording profile/settings and permissions yourself; they have not been remotely verified.

## During the task

Follow RECORDING-GUIDE.md. Make the small SQL repair yourself on camera. Use mouse selection, table browsing, result sorting, tab navigation and export dialogs when those actions help the analysis. Explain what, where and why. Pause about one second after clicks. Keep typing in short bursts and never introduce aimless cursor motion to fill time.

You will save:

- **Final Output 1.sql:** corrected query, decision comments, verification and comparison statements that you actually create/adapt during recording.
- **Final Output 2.csv:** before/after eligibility for all ten original builds, including decision reasons.
- **Final Output 3.csv:** main and five boundary scenarios, with expected/actual counts plus missing, unexpected and duplicate rows.

Use learning_reference to learn the SQL before recording. During recording explain and construct the checks; do not substitute finished reference outputs afterward.

## Export a result grid

Run the comparison statement so its result grid is active. Right-click inside the grid → **Export Data** (some versions say Export Resultset) → **CSV** → choose file path **Deliverables/Final Output 2.csv**. Include column headers, UTF-8, comma delimiter. Finish and check the destination/preview. Export the verification grid the same way as Final Output 3.csv. Names and wizard pages depend on DBeaver version; rehearse before recording.

## Expected observations (not claimed tested)

Old main query: zero rows. Corrected main query: seven named builds. B002/B005 withheld; unknown row 10 withheld.

Before/after table: ten rows, old_result withheld for every row, corrected_result eligible for the seven listed IDs.

Verification counts: main 7; null_entry 2; duplicate_entry 2; empty_exclusions 3; matching_entry 2; unknown_build 1. All missing_ids, unexpected_ids and duplicate_rows must be zero. These are designed expectations; prepared SQL has not been executed or tested here. Rehearse and resolve any difference before recording.

## After recording

Do not upload this preparation folder. Copy the actual task-used original inputs and actual recorded outputs flat into Deliverables. Preserve Input 1.sqlite unchanged and use the original file for packaging, excluding driver/cache/journal files. Do not include Goal, guides, learning_reference, empty templates or a preparation README. No final ZIP or completed Metadata.rtf is being represented as ready now.

Keep the new MP4 and matching original TaskRecorder recording_*.zip separately. Bring back this recording attempt's files; Metadata and Studio confirmations must be completed against the actual recording. See METADATA-PLAN.md and FILE-MAP.md. Source material is synthetic and AI-generated before recording; record that provenance accurately.
