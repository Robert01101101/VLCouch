# Contributing to VLCouch

Thanks for helping improve VLCouch. PRs are welcome.

**Windows-first** — use PowerShell from the repo root (`.\dev.ps1`, `.\scripts\test.ps1`).

## Getting started

See [README.md](README.md) for setup, configuration, and features. For architecture and file locations, see [AGENTS.md](AGENTS.md).

## Before you submit

Run the test layer that matches your change, then the full suite before merge:

```powershell
.\scripts\test.ps1              # full suite
.\scripts\test.ps1 -Layer api   # backend pytest
.\scripts\test.ps1 -Layer unit  # frontend Vitest
.\scripts\test.ps1 -Layer e2e   # Playwright
```

## Do not commit

- `.env` (real `MEDIA_ROOTS`)
- `backend/data/library.db`
- User media files

Tests use fixture media under `backend/tests/fixtures/media/` with `APP_ENV=test`.

## License

By contributing, you agree that your contributions are licensed under the project's GPL-3.0 license.
