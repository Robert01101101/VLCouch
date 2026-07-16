# AGENTS.md — VLCouch

Guide for AI agents implementing and verifying changes in this repo.

## Stack

- **Backend:** Python 3, FastAPI, SQLModel, SQLite (`backend/app/`)
- **Frontend:** Vite + React + Tailwind (`frontend/src/`)
- **Playback:** VLC subprocess (Windows); ffmpeg for thumbnails
- **Shell:** PowerShell on Windows

## Architecture overview

```
MEDIA_ROOTS (.env)
    → library_scan.scan_library() + scanner.py (guessit parsing)
    → SQLite (movies, shows, episodes, watch progress)
    → FastAPI routers (browse, play, watch, settings)
    → frontend/src/api.js
    → React pages (Home hero + rows, ShowDetail, Settings)
    → POST /api/play/{type}/{id} → vlc.py launches VLC
    → watch progress + thumbnails updated on play / mark watched
```

**Browse flow:** `GET /api/browse` returns a hero item (up-next episode or rewatch movie) and curated rows (recently watched, TV themes, movie decades/genres). The frontend renders `HeroBanner` and `Row` components with poster cards.

**Play/watch flow:** Play triggers VLC via the play router; watch status is stored in SQLite. Thumbnails are generated lazily by `thumbnail_service.py` when items are played or marked watched.

With the backend running, inspect all endpoints and schemas at **http://localhost:8000/docs** (OpenAPI).

## Commands

| Task | Command |
|------|---------|
| Dev servers | `.\dev.ps1` → http://localhost:5173 |
| All tests | `.\scripts\test.ps1` |
| API tests only | `.\scripts\test.ps1 -Layer api` |
| Unit tests only | `.\scripts\test.ps1 -Layer unit` |
| E2E tests only | `.\scripts\test.ps1 -Layer e2e` |
| Manual scan smoke | `cd backend; python scripts/smoke_scan.py` |

## Where to edit

| Task | Primary files |
|------|---------------|
| Home browse rows, hero, search | `backend/app/routers/library.py` |
| Filename / folder parsing | `backend/app/scanner.py` |
| Scan orchestration | `backend/app/library_scan.py` |
| Thumbnail extraction | `backend/app/thumbnail_service.py`, `backend/app/thumbnail_jobs.py` |
| VLC launch | `backend/app/routers/play.py`, `backend/app/vlc.py` |
| Watch status | `backend/app/routers/watch.py`, `backend/app/watch_service.py` |
| Settings persistence | `backend/app/routers/settings.py`, `backend/app/settings_store.py` |
| Wikipedia metadata | `backend/app/metadata.py` |
| DB models | `backend/app/models.py`, `backend/app/db.py` |
| App startup, scan trigger | `backend/app/main.py` |
| Frontend API client | `frontend/src/api.js` |
| Home page + hero UI | `frontend/src/pages/Home.jsx`, `frontend/src/components/HeroBanner.jsx`, `frontend/src/components/Row.jsx` |
| Show detail / episodes | `frontend/src/pages/ShowDetail.jsx` |
| Search bar | `frontend/src/components/SearchBar.jsx` |
| Settings page | `frontend/src/pages/Settings.jsx` |
| Poster cards | `frontend/src/components/PosterCard.jsx` |
| Routing / nav | `frontend/src/App.jsx` |

## Commit messages

Before committing, use the **generate-commit-message** skill (`.cursor/skills/generate-commit-message/`) to draft a human-readable subject, summary, and outcome-focused bullets from the diff.

## Verification checklist

After every feature change:

1. Run the relevant test layer (see skills in `.cursor/skills/`)
2. Fix failures; re-run until green
3. Before declaring done, run `.\scripts\test.ps1 -Layer all`
4. If you changed testids, endpoints, env vars, or file layout, run the **maintain-agent-docs** skill (`.cursor/skills/maintain-agent-docs/`)

## Known pitfalls

- **db.engine import:** Import `app.db as db` and use `db.engine` after test overrides — not `from app.db import engine`
- **TEST_MODE:** Set `TEST_MODE=true` in tests to skip VLC launch and background thumbnail jobs
- **Windows paths:** SQLite and media paths must handle backslashes; see `backend/app/db.py`
- **SCAN_LIMIT vs rescan:** `SCAN_LIMIT` caps startup scans only; **Rescan Library** always scans the full library
- **E2E ports:** E2E uses isolated ports (backend 8001, frontend 5174) so dev servers are unaffected

## Do not touch

- Developer `.env` (real `MEDIA_ROOTS`)
- `backend/data/library.db` (production database)
- User media files on disk

Tests use `APP_ENV=test` with fixture media in `backend/tests/fixtures/media/`.

## Adding a new feature

| Layer | Add |
|-------|-----|
| API endpoint | Test in `backend/tests/test_*_api.py` |
| Scanner/parser | Test in `backend/tests/test_scanner.py` |
| React component | Test in `frontend/src/**/*.test.jsx` |
| User flow | Playwright spec in `e2e/specs/` |
| Interactive UI | `data-testid` on buttons, rows, cards (see `.cursor/rules/selectors.mdc`) |
| Env var | `.env.example` (+ update docs via maintain-agent-docs skill) |

## Self-correction loop

```
implement → run targeted tests → read failure output → fix → re-run → full suite
```

On Playwright failure: `npx playwright show-report` from repo root.

## Project layout

```
backend/app/          # FastAPI application
backend/tests/        # pytest suite + fixtures
frontend/src/         # React UI
e2e/specs/            # Playwright E2E tests
scripts/test.ps1      # unified test runner
.cursor/skills/       # agent self-verification skills
```

## Agent skills

Skills in `.cursor/skills/` guide verification and common workflows:

| Skill | Use when |
|-------|----------|
| `verify-backend` | Changes under `backend/app/` — run pytest API layer |
| `verify-frontend` | React components, pages, or `api.js` — run Vitest |
| `verify-e2e` | UI flows — run Playwright specs |
| `verify-scanner` | `scanner.py`, `library_scan.py`, or fixture media |
| `verify-thumbnails` | Thumbnail cache, extraction, or background jobs |
| `add-api-endpoint` | New backend route end-to-end (router, tests, UI) |
| `maintain-agent-docs` | Sync AGENTS.md, selectors, verify skills, CONTRIBUTING.md |
| `generate-commit-message` | Draft commit message from the diff before committing |

## Related docs

- [CONTRIBUTING.md](CONTRIBUTING.md) — PR guidelines for human contributors
- [README.md](README.md) — user setup and configuration
- `.cursor/skills/maintain-agent-docs/` — keep this file and selector rules in sync with code
