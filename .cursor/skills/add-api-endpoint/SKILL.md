---
name: add-api-endpoint
description: End-to-end recipe for adding a new API endpoint — router, tests, api.js, UI, and verification. Use when implementing a new backend route that the frontend will call.
---

# Add API endpoint

End-to-end checklist for a new user-facing API feature.

## Steps

1. **Add route** in the appropriate router under `backend/app/routers/` (or `main.py` for scan/health-style routes). Use `prefix="/api"` and return a response dict.
2. **Add test** in `backend/tests/test_*_api.py` (create a new file if no existing test module fits).
3. **Add function** in `frontend/src/api.js` — path must match the router (see `api-contract.mdc`).
4. **Wire UI** — call the new api.js function from a component or page.
5. **Add `data-testid`** on new interactive elements per `selectors.mdc`.
6. **Add component test** if the UI has non-trivial behavior (`frontend/src/**/*.test.jsx`).
7. **Add E2E spec** in `e2e/specs/` if the change is a user-facing flow.
8. **Run verification layers:**
   - `.\scripts\test.ps1 -Layer api` (backend)
   - `.\scripts\test.ps1 -Layer unit` (frontend, if UI changed)
   - `.\scripts\test.ps1 -Layer e2e` (if user flow changed)
   - `.\scripts\test.ps1 -Layer all` before declaring done
9. **Run maintain-agent-docs checklist** — see `.cursor/skills/maintain-agent-docs/SKILL.md` (update `api-contract.mdc` endpoint table, test file maps in verify-* skills, and AGENTS.md if layout changes).

## Notes

- Use `from app.db import get_session` and `import app.db as db` in routers/tests
- `TEST_MODE=true` skips VLC launch and thumbnail background jobs in tests
- Load domain skills as needed: `verify-backend`, `verify-frontend`, `verify-e2e`, `verify-scanner`, `verify-thumbnails`
