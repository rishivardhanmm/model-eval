---
name: task-id-recording-prep
description: Prepares all supporting materials for a request in the template "Task - [hex ID] Goal: ... Starting point: ... Apps and tools: ... Deliverable: ... [How I will check the result: ...] Prior work and reuse: ...", where the user will perform a short (usually 15-20 min) screen recording in one or more real apps (often 2-3, sometimes a single app such as VS Code). Use when a message arrives in this template format, or when the user references an existing "Task - [ID]" folder and asks to continue or update it.
---

# Task-ID Recording Prep

Prepares the folder structure, the tabbed HTML planning report, any reusable script deliverable, and draft text for manually-performed steps, for a task given in the structured template:

```
Task - <hex ID> Goal: <description, usually a 15-20 min screen recording across 2-3 apps>
Starting point: <what already exists>
Apps and tools: <declared app list, each with edition/license>
Deliverable: <what must come out of this>
How I will check the result: <acceptance checks>      <- optional section; newer tasks include it
Prior work and reuse: <whether this continues an earlier task>
```

Treat the `Goal` / `Deliverable` / `Starting point` / `How I will check the result` text as a literal spec to fulfill precisely — don't add scope, don't narrow it. "No inclusion or exclusion" if the user says that. Anything the user writes *after* the template (e.g. "make sure no inclusions/exclusions") is an instruction to you, not task text — never paste it into the verbatim Task tab.

If the task states no time budget, use the 15-20 min default and say so in the Script tab's timing note.

## Step 1: Set up the folder structure

Create, under the current working directory:

```
Task - <full hex ID>\            <- outer folder, literally "Task - " + the complete ID (not a short prefix)
  Task-Report.html                <- lives directly here, NOT nested one level deeper
  <short descriptive title>\      <- subfolder for everything else, named for the task's subject
    ...supporting deliverables...
```

This exact split (HTML report at the outer level, everything else one level deeper under a title folder) was arrived at after several corrections on a prior task — see the "why" below. Don't improvise a different layout.

**Windows file-lock gotcha:** before any rename/move of the task folder (or a subfolder), make sure your own shell's cwd isn't inside it — Windows reports a confusing "Device or resource busy" / "Permission denied" if the current process (or a File Explorer window, or an editor) has that exact directory open. If a rename fails this way, `cd` out of it yourself first and retry; if it still fails, ask the user to close any Explorer/VS Code window browsing that folder (checking one level deeper too — the lock can be on a subfolder specifically, not just the top folder) rather than forcing anything.

**When the Starting point describes existing code or files** (e.g. "a small local Python module with X, no Y"), build that pre-existing state in its own folder (e.g. `<title>\starting_point\`) and put the finished solution in a separate folder (e.g. `<title>\reference\`). The recording opens on the starting-point state; the reference folder is what the user types from and what you verify. Keep the starting point minimal — exactly what the text says exists, nothing the Goal says gets added.

## Step 2: Build Task-Report.html

Start from `references/report-template.html` in this skill — it's a complete, self-contained, verified single-file HTML with working tab-switching JS and a Python-aware comment colorizer already wired up. Copy it to `Task-Report.html` and replace the `{{PLACEHOLDER}}` tokens with real content. Don't rewrite the CSS/JS from scratch — it's already been tag-balance-checked and the colorizer has been tested against real code containing `#` characters inside string literals (see `references/colorizer-notes.md` for why that matters).

The report has up to seven tabs, **in this order** (the user asked for this layout: Task first, simple and crisp, every detail present, nothing that deviates from the task text). Prefer tables and short bullets over paragraphs everywhere.

1. **Task** (first tab, opens active) — the original task text reproduced verbatim: Goal, Starting point, an Apps/tools table (declared app, edition/license, App-use scope paragraph, App-use record ID; copy any line above the list such as "1. Multiple apps"), Deliverable, How I will check the result (when present), Prior work and reuse. Zero additions or omissions — copy the literal text into the blockquotes.
2. **Analysis** — a short context paragraph; a deliverables table (one row per deliverable the task names — no more, no fewer — with form and the app it is made in); an inputs table (file, rows, columns, contents); key definitions the numbers depend on; the verified headline results the user should expect on screen; and how the work flows across the apps (2+ apps: "Why it is structured across multiple apps"; a single app: "How the work flows in <App>"). Skimmed once before recording — if a sentence doesn't change what the user does on camera, cut it.
3. **Plan** — build-order table (phase, app, action, output), a "pre-staged vs. created on camera" table, and the before-pressing-record checklist.
4. **Script** — start-of-recording checklist, minute-by-minute on-camera flow whose time ranges sum to roughly the time budget, end-of-recording checklist, timing note.
5. **Notes** — only if a deliverable is hand-typed into an app (Notes, Word, …): a table of each note section (what it says, why it is there, where its numbers appear on screen) plus the full draft text from Step 4 to retype.
6. **Checks** — only if the task has `How I will check the result`: one row per check clause mapped to the exact proof (printed PASS line, query output, column, file); expected values and hand-check cases; thresholds with their reasoning; the failure cases you planted and verified.
7. **Code Walkthrough** — only if the task involves writing code. See Step 3. Order files the way they are built on camera; non-Python files (SQL, etc.) go in a plain block. With several Python files, repeat the clean+annotated pair once per file; every Python `<code>` element must carry `class="py-src"` (the colorizer selects by that class).

Delete the button and panel for any tab that doesn't apply, and keep each `showTab('<id>')` button matching its panel id.

Fill in the header's `Task - {{TASK_ID}}` field and the footer's matching field with the full ID — not a shortened prefix, and not "Task ID: ..." phrasing.

After filling in placeholders, validate the result the same way (tag balance, no leftover `{{...}}` tokens):

```
python -c "
import re
html = open('Task-Report.html', encoding='utf-8').read()
assert not re.findall(r'\{\{\w+\}\}', html), 'leftover placeholders!'
assert html.count('<div') == html.count('</div>')
assert html.count('<table') == html.count('</table>')
assert html.count('<pre') == html.count('</pre>')
ids = re.findall(r'<div id=\"(\w+)\" class=\"panel', html)
assert ids == re.findall(r\"showTab\('(\w+)'\)\", html), 'tab buttons and panels differ'
print('OK')
"
```

Then render each tab (e.g. headless Chrome `--screenshot` with that panel set `active`) and look at it before reporting done. Avoid writing literal tags like `<code>` inside HTML comments — they skew tag-balance counts.

## Step 3: If there's a code deliverable

Write the actual script to its real path under the title subfolder (e.g. `<title>\script\<name>.py`), favoring the standard library over extra dependencies so the team can run it with zero setup. **Check what is actually installed before choosing a dependency** (`python -c "import matplotlib"` etc.). If a plot is required and matplotlib is missing, write the chart as a hand-built SVG with the standard library instead of pip-installing anything, and load the `dataviz` skill before writing the chart code. Keep the full run to a few seconds so it can be executed on camera.

If the task has acceptance checks (`How I will check the result`), the script must compute and print each one explicitly (pass/fail per check, as `[PASS]`/`[FAIL]` lines, exit code 1 on any failure — and bad input such as a constraint violation or a malformed export must produce a FAIL line, not a traceback), and you must fix each threshold (tolerance, bound) **before** looking at results, with the reasoning written down in the README/report. Reproducibility checks compare the full saved state (e.g. a SHA-256 digest of it), not just the final numbers. Generated outputs (CSV, SVG) must be byte-identical across two runs: no timestamps, no `hash()`.

Then produce **two** copies for the Code Walkthrough tab:
1. **Clean version** (the real deliverable) — concise, with a Google-style docstring (`Args:`/`Returns:`) on every function, no line-by-line inline comments.
2. **Annotated version** (a second file, e.g. `<name>_annotated.py`, for teaching/narration only) — identical logic, with a real Python `#` comment on nearly every meaningful line, explaining what that line does and why.

Before embedding either into the HTML:
- `python -m py_compile` both files.
- Run both against the same sample input and diff the output — it must be byte-identical (stdout *and* any generated files). If it isn't, the annotated copy has a bug; fix it before moving on. When there are several files, annotate each one; an annotated driver may import the annotated module (the only allowed token difference).

Escape each file's raw text (`html.escape(open(path).read())`) and place it inside its own `<pre><code class="py-src">...</code></pre>` block in the template — the embedded JS tokenizer colors `#` comments amber and docstrings in muted italic automatically at page-load; you don't need to pre-color anything yourself.

## Step 4: Steps the user will perform manually, live, on camera

If the Goal says something like "I will write/prepare/type ... in <App>" for an app Claude can't drive directly from this machine (Apple Notes on macOS, a live Word session, etc.) — do **not** pre-build the finished file for that step. No generated `.docx`, no populated Notes export.

Instead, write a plain-text draft (e.g. `notes\column_contract.txt`, `word\<name>_draft.txt`) that the user reads and manually retypes into the real app during the recording. This mirrors how a human would actually jot a quick spec before a meeting, or draft a note before typing it up — producing the finished artifact yourself would defeat the point of the recording.

## Step 5: Never embed personal info

Don't put the user's real name, email, or other identifying info into any generated artifact (HTML, scripts, drafts, sample data) — not even as a harmless-looking "Prepared by:" line — unless the user explicitly asks for attribution in that specific file. This caught a real mistake on a prior run: a generated Word doc had "Prepared by: <user's real email>" baked in, which the user found objectionable and asked to have removed, along with being told the Word step didn't need a finished file at all (see Step 4).

## Step 6: Sample/demo data (if the task needs it)

If the task calls for synthetic sample data (e.g. comparing a "baseline" vs a "drifted" export), build small, clearly-synthetic files (not real records) with the specific planted differences the Goal describes (a rename, a new field, a format inconsistency, etc.) — and verify any checker/comparison script actually detects each planted difference before calling the task done.

When a check says "compare examples with hand-calculated cases" in a GUI tool (e.g. DBeaver), provide a query that outputs the tool's *classification* per example (e.g. retained_30d/60d/90d flags), not only the raw dates — otherwise the user compares their arithmetic with itself. Put the expected values in the Checks tab.

Practical run-sheet details that caused trouble before: SQLite foreign keys are per connection (run `PRAGMA foreign_keys = ON` in DBeaver too); state DBeaver CSV export settings (header top/label, plain numbers); an SVG opens as XML text in VS Code unless reopened with Image Preview; git drops empty folders (prep step: create `exports/` if missing); a recording with Notes.app means macOS, so use `python3`.

## Step 7: Commit message

When the user asks for a commit message, give **one line** matching the repo's previous task commits (check `git log --oneline`), e.g.:

```
feat: add <title-slug> task (<full hex ID>)
```

Don't commit unless asked, and stage only the new task folder.

## Step 8: Report back

Tell the user the final folder path, what's inside it, and confirm:
- the HTML report opens with no leftover placeholders and every included tab (Task first) working,
- any script runs and was verified against sample data,
- no personal info is anywhere in the output,
- nothing outside the new task folder was modified.
