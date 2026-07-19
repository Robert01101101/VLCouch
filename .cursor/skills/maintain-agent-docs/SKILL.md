---
name: maintain-agent-docs
description: Keep AGENTS.md, selector rules, verify skills, and CONTRIBUTING.md in sync with code. Use after adding or changing data-testid values, API endpoints, env vars, test file locations, project structure, or verification commands.
---

# Maintain agent documentation

## When to use

Run this checklist after you:

- Add or change `data-testid` in `frontend/src/`
- Add or change API routes under `backend/app/routers/`
- Add env vars to `backend/app/config.py` or `docs/.env.example`
- Add test files under `backend/tests/`, `frontend/src/`, or `e2e/specs/`
- Move modules or change the scan → browse → play architecture
- Change commands in `scripts/test.ps1`, `scripts/dev.ps1`, or `README.md`

## Checklist

### 1. Sync selector table

Grep all current test IDs:

```powershell
rg 'data-testid' frontend/src/ -n
rg 'testId=' frontend/src/ -n
```

Update `.cursor/rules/selectors.mdc` so every pattern in code is listed (single source of truth). Include dynamic patterns like `browse-row-{slug}` and `poster-card-{type}-{id}`.

### 2. Update AGENTS.md feature table

If you added a new test layer or file type, extend the **Adding a new feature** table in `AGENTS.md`. Example: a new router needs a row pointing to `backend/tests/test_*_api.py`.

### 3. Update verify-* skill test maps

| Skill | File | Update when |
|-------|------|-------------|
| `verify-backend` | `.cursor/skills/verify-backend/SKILL.md` | New/changed `backend/tests/test_*.py` |
| `verify-frontend` | `.cursor/skills/verify-frontend/SKILL.md` | New/changed `frontend/src/**/*.test.jsx` |
| `verify-e2e` | `.cursor/skills/verify-e2e/SKILL.md` | New/changed `e2e/specs/*.spec.ts` |

Grep test files to confirm coverage:

```powershell
rg '^def test_|^test\(' backend/tests/ -l
Get-ChildItem frontend/src -Recurse -Filter *.test.jsx | Select-Object -ExpandProperty Name
Get-ChildItem e2e/specs -Filter *.spec.ts | Select-Object -ExpandProperty Name
```

### 4. Update AGENTS.md architecture / file map

When you add modules or move responsibilities, update **Architecture overview** and **Where to edit** in `AGENTS.md`. Key paths:

| Area | Path |
|------|------|
| Browse API, hero, search | `backend/app/routers/library.py` |
| Play / VLC | `backend/app/routers/play.py`, `backend/app/vlc.py` |
| Watch status | `backend/app/routers/watch.py`, `backend/app/watch_service.py` |
| Settings API | `backend/app/routers/settings.py`, `backend/app/settings_store.py` |
| Filename parsing | `backend/app/scanner.py` |
| Full scan orchestration | `backend/app/library_scan.py` |
| Thumbnail jobs | `backend/app/thumbnail_service.py`, `backend/app/thumbnail_jobs.py` |
| Frontend API client | `frontend/src/api.js` |
| Home / hero UI | `frontend/src/pages/Home.jsx`, `frontend/src/components/HeroBanner.jsx` |

### 5. Env vars

If you add a config variable:

1. Add it to `docs/.env.example` with a short comment
2. If tests depend on it, add to `docs/.env.test.example` and mention in `AGENTS.md` **Known pitfalls** or **Do not touch**
3. Document in `README.md` configuration table if user-facing

Grep for config reads:

```powershell
rg 'os\.environ|getenv|Field\(' backend/app/config.py backend/app/ -n
```

### 6. Cross-check commands

Ensure `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `.cursor/rules/project.mdc` agree on:

- `.\scripts\dev.ps1` for local dev
- `.\scripts\test.ps1` and `-Layer api|unit|e2e|all`

```powershell
rg 'test\.ps1|dev\.ps1' README.md AGENTS.md CONTRIBUTING.md .cursor/rules/
```

### 7. OpenAPI

New endpoints appear automatically at http://localhost:8000/docs when the backend is running. Mention in `AGENTS.md` if agents need to discover request/response shapes.

## Self-correction loop

```
change code → grep testids/endpoints/tests → update selectors.mdc + AGENTS.md + verify skills → cross-check README
```

## Notes

- Do not commit `.env` or `backend/data/library.db`
- Selector rule applies to `frontend/src/**` via `.cursor/rules/selectors.mdc`
- Human contributors: point them to `CONTRIBUTING.md`, which links here
