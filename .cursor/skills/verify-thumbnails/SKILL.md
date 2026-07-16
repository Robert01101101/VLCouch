---
name: verify-thumbnails
description: Run thumbnail tests after changes to cache, extraction, or background thumbnail jobs. Use when modifying thumbnail_service.py, thumbnails.py, or thumbnail_jobs.py.
---

# Verify thumbnail changes

## When to use

After changes to:

- `backend/app/thumbnails.py` — cache paths, ffmpeg extraction, `THUMBNAIL_CACHE_VERSION`
- `backend/app/thumbnail_service.py` — background task queuing
- `backend/app/thumbnail_jobs.py` — movie/show thumbnail generation

## Steps

1. Run API tests:
   ```powershell
   .\scripts\test.ps1 -Layer api
   ```
2. Focus on thumbnail tests:
   ```powershell
   cd backend
   $env:APP_ENV="test"; $env:TEST_MODE="true"
   .\.venv\Scripts\pytest tests/test_thumbnails.py -q
   ```
3. Fix failures; re-run until green, then run full api layer

## Test file map

| File | Covers |
|------|--------|
| `test_thumbnails.py` | seek seconds, cache path versioning, stale cache cleanup |
| `test_play_api.py` | play endpoint queues thumbnails (skipped in TEST_MODE) |
| `test_watch_api.py` | watch-status queues thumbnails (skipped in TEST_MODE) |

## Self-correction loop

```
run test_thumbnails.py → read traceback → fix thumbnails/jobs → re-run → full api layer
```

## Notes

- Bump `THUMBNAIL_CACHE_VERSION` in `thumbnails.py` when seek logic, ffmpeg params, or cache layout changes — this invalidates old cached files on startup
- `TEST_MODE=true` skips thumbnail background jobs (same as VLC skip); unit tests in `test_thumbnails.py` call thumbnail functions directly
- Poster URLs are served at `/posters/{filename}`; cache files live under `POSTERS_DIR`
