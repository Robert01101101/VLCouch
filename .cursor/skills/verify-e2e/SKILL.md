---
name: verify-e2e
description: Run Playwright E2E browser tests to verify UI flows end-to-end. Use before declaring work complete, after UI flow changes, or when browser behavior must be validated.
---

# Verify E2E flows

## When to use

- Before declaring any UI-related task complete
- After changes to pages, navigation, play/watch flows
- When unit tests pass but user-facing behavior needs confirmation

## Steps

1. Run E2E suite (starts test backend + Vite automatically):
   ```powershell
   .\scripts\test.ps1 -Layer e2e
   ```
2. On failure, view the HTML report:
   ```powershell
   npx playwright show-report
   ```
3. Fix using `data-testid` selectors; re-run:
   ```powershell
   npx playwright test e2e/specs/home.spec.ts
   ```
4. Run full suite before done: `.\scripts\test.ps1 -Layer all`

## Expected flows

| Spec | Flow |
|------|------|
| `home.spec.ts` | Home loads → browse rows visible → rescan button works |
| `show-detail.spec.ts` | Click show poster → detail page → toggle watched |
| `play.spec.ts` | Hover movie card → Play (TEST_MODE skips VLC) |

## Self-correction loop

```
run playwright → read trace/report → fix UI or spec → re-run affected spec → run full e2e layer
```

## Notes

- E2E uses **isolated ports** (backend 8001, frontend 5174) so your dev servers and VLC are not affected
- E2E backend uses `APP_ENV=test`, `TEST_MODE=true` (no VLC launch), `SCAN_ON_STARTUP=true` with fixture media
- Prefer `page.getByTestId(...)` over text selectors
- For async UI updates (e.g. watched checkbox), use `click()` + `waitForResponse`, not `check()`
