---
name: verify-frontend
description: Run Vitest component tests after React component or page changes. Use when modifying frontend/src/ components, pages, or api.js mocks.
---

# Verify frontend changes

## When to use

After changes to `frontend/src/components/`, `frontend/src/pages/`, or `frontend/src/api.js`.

## Steps

1. Run unit tests:
   ```powershell
   .\scripts\test.ps1 -Layer unit
   ```
2. On failure, run a single file for faster iteration:
   ```powershell
   cd frontend
   npm test -- --run src/pages/Home.test.jsx
   ```
3. Fix and re-run until green
4. If the change affects user flows, also run E2E (see `verify-e2e` skill)

## Test file map

| File | Covers |
|------|--------|
| `PosterCard.test.jsx` | card render, play button |
| `HeroBanner.test.jsx` | hero content, play button, playItem callback |
| `Row.test.jsx` | row title, cards, empty state |
| `SearchBar.test.jsx` | search input, results display |
| `Home.test.jsx` | loading, error, browse rows, hero banner |
| `ShowDetail.test.jsx` | episodes, watched toggle, season bulk watch |
| `Settings.test.jsx` | settings page, toggles, rescan |

## Self-correction loop

```
run vitest → read DOM/assertion error → fix component or test → re-run file → run full unit layer
```

## Notes

- API calls are mocked via `vi.mock('../api')`
- Use `data-testid` selectors in tests, not duplicate text matches
- Wrap routed components in `<MemoryRouter>` in tests
