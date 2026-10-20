# dev

Browser-level checks for the local web UI.

```bash
uv run python dev/web_e2e.py
```

Starts `dev/serve_web.py` on port 8150 with temporary workbooks, drives the
system Chromium through Playwright, and checks:

- a jumbled workbook is rejected and removed;
- a valid second workbook replaces the sheet list;
- the upload status and summary update;
- Run writes a manifest naming the uploaded workbook;
- a `.docx` upload is rejected.

Screenshots land in `dev/artifacts/`.
