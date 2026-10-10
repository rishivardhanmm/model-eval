# Why the comment colorizer is a real tokenizer, not a regex

The embedded `colorizePython()` JS in `report-template.html` walks the source text character by character and tracks whether it's inside a string literal before treating a `#` as the start of a comment.

This matters because real validation/report code tends to contain `#` characters *inside* string literals that must not be colored as comments — for example a message like:

```python
f"customer_id '{cid}' does not match CUST-###### format."
```

A naive `line.split('#')[0]` or `/#.*/` regex approach will treat the first `#` inside that string as the start of a comment and mis-color everything after it, including the real code that follows on the same line in some cases.

The tokenizer handles:
- `#` outside any string -> starts a comment, runs to end of line, wrapped in `<span class="cmt">`.
- Triple-quoted strings (`'''...'''` or `"""..."""`) -> wrapped in `<span class="doc">`, scanned for the matching closing triple-quote (can span multiple lines — this is how function docstrings render).
- Single/double-quoted strings -> scanned to the matching closing quote, respecting backslash-escapes, left as plain code color (not specially colored) — this is what keeps a `#` inside `"CUST-######"` from being swallowed as a comment.
- A whole-line comment (nothing but whitespace before the `#`) additionally gets the `cmt-line` class, which gives it a full-width highlighted background band (the "git diff" look) — an inline trailing comment just stays colored text next to its code, no band.

**Before trusting this for a new file:** if you ever change the tokenizer, re-verify it the same way it was originally verified — run the exact JS under Node against the real annotated source file and assert:
1. A known in-string `#...#` sequence survives intact (not swallowed as a comment).
2. A real inline comment actually gets wrapped.
3. A docstring actually gets wrapped.
4. `<span>`/`</span>` counts balance (no stray unclosed tags).

Don't just eyeball the HTML — the string-vs-comment distinction is exactly the kind of thing that looks fine on simple input and breaks silently on the first file with a `#` in a string.
