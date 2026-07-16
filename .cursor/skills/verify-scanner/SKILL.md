---
name: verify-scanner
description: Run scanner and library-scan tests after changes to file parsing, scan orchestration, or fixture media. Use when modifying scanner.py, library_scan.py, genre_tags.py, or backend/tests/fixtures/media/.
---

# Verify scanner changes

## When to use

After changes to:

- `backend/app/scanner.py` — filename parsing, show/movie detection
- `backend/app/library_scan.py` — scan orchestration, DB population
- `backend/app/genre_tags.py` — genre normalization
- `backend/tests/fixtures/media/` — test media layout

## Steps

1. Run API tests (scanner tests live in the api layer):
   ```powershell
   .\scripts\test.ps1 -Layer api
   ```
2. Focus on scanner tests for faster iteration:
   ```powershell
   cd backend
   $env:APP_ENV="test"; $env:TEST_MODE="true"
   .\.venv\Scripts\pytest tests/test_scanner.py -q
   ```
3. For manual smoke against fixture media:
   ```powershell
   cd backend
   python scripts/smoke_scan.py
   ```
4. Fix failures; re-run until green, then run full api layer

## Test file map

| File | Covers |
|------|--------|
| `test_scanner.py` | `scan_library`, episode parsing, supplemental content, fixture media |
| `test_library_api.py` | browse/movies/shows after scan (indirect scanner coverage) |

## Self-correction loop

```
run test_scanner.py → read traceback → fix scanner/library_scan → re-run → smoke_scan.py → full api layer
```

## Notes

- Tests use fixture media in `backend/tests/fixtures/media/`; never scan the developer's real `MEDIA_ROOTS`
- Import `app.db as db` and use `db.engine` in tests after overrides
- `SCAN_LIMIT` in config can cap files during dev scans; tests use isolated DB via `tmp_path`
