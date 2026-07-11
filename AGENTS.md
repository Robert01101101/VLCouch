# AGENTS.md — VLCouch

Guide for AI agents implementing and verifying changes in this repo.

## Stack

- **Backend:** Python 3, FastAPI, SQLModel, SQLite (`backend/app/`)
- **Frontend:** Vite + React + Tailwind (`frontend/src/`)
- **Playback:** VLC subprocess (Windows); ffmpeg for thumbnails
- **Shell:** PowerShell on Windows

## Commands

| Task | Command |
|------|---------|
| Dev servers | `.\dev.ps1` → http://localhost:5173 |
| All tests | `.\scripts\test.ps1` |
| API tests only | `.\scripts\test.ps1 -Layer api` |
| Unit tests only | `.\scripts\test.ps1 -Layer unit` |
| E2E tests only | `.\scripts\test.ps1 -Layer e2e` |
| Manual scan smoke | `cd backend; python scripts/smoke_scan.py` |

## Commit messages

Before committing, use the **generate-commit-message** skill (`.cursor/skills/generate-commit-message/`) to draft a human-readable subject, summary, and outcome-focused bullets from the diff.

## Verification checklist

After every feature change:

1. Run the relevant test layer (see skills in `.cursor/skills/`)
2. Fix failures; re-run until green
3. Before declaring done, run `.\scripts\test.ps1 -Layer all`

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
