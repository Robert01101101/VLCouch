---
name: verify-backend
description: Run and fix backend pytest tests after API, scanner, model, or router changes. Use when modifying backend/app/, adding endpoints, or when API tests fail.
---

# Verify backend changes

## When to use

After any change under `backend/app/` — routers, models, scanner, config, VLC/thumbnails.

## Steps

1. Run API tests:
   ```powershell
   .\scripts\test.ps1 -Layer api
   ```
2. If failures occur, read the pytest output carefully
3. Fix the smallest issue; re-run only the failing file:
   ```powershell
   cd backend
   $env:APP_ENV="test"; $env:TEST_MODE="true"
   .\.venv\Scripts\pytest tests/test_library_api.py -q
   ```
4. Repeat until green

## Test file map

| File | Covers |
|------|--------|
| `test_health.py` | `GET /api/health` |
| `test_library_api.py` | browse, movies, shows, show detail |
| `test_watch_api.py` | watch-status, continue-watching |
| `test_play_api.py` | play endpoint, TEST_MODE VLC skip |
| `test_scanner.py` | scan_library against fixture media |

## Self-correction loop

```
run pytest → read traceback → fix code → re-run failing file → run full api layer
```

## Notes

- Tests use isolated SQLite via `tmp_path`; never touch `backend/data/library.db`
- `TEST_MODE=true` skips VLC and thumbnail background jobs
- Import `app.db as db` and use `db.engine` after overrides (not `from app.db import engine`)
