# dev

Browser-level checks for the local web UI.

## Fast interaction matrix

```bash
uv run pytest dev/test_web_modes.py -q
```

29 scenarios, ~22 s. Three long-lived servers (valid / seeded / empty),
one Chromium, one context per test. Covers validation, upload collisions,
jumbled and `.docx` rejection, pipeline run + manifest, results downloads,
navigation, all nine tools, error paths, RU/EN, and duplicate-UI checks.

## Single smoke run

```bash
uv run python dev/web_e2e.py
```

Starts `dev/serve_web.py` on port 8150 with temporary workbooks and checks the
upload flow end to end. Screenshots land in `dev/artifacts/`.
