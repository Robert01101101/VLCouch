# Contributing to VLCouch

Thanks for helping improve VLCouch. PRs are welcome.

**Windows-first** — use PowerShell from the repo root (`.\scripts\dev.ps1`, `.\scripts\test.ps1`).

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

## Releasing a Windows installer

See the **release-version** skill (`.cursor/skills/release-version/`) for the full agent workflow. Summary:

1. Bump [`VERSION`](VERSION) at the repo root.
2. Ensure `e2e/specs/settings.spec.ts` uses `e2e/helpers/appVersion.ts` (no hardcoded semver).
3. Run `.\scripts\test.ps1 -Layer all` — commit the bump **only if all tests pass**.
4. Push to `main`, then create and push a matching tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
5. GitHub Actions ([`.github/workflows/release.yml`](.github/workflows/release.yml)) builds `dist/staging/`, compiles `VLCouchSetup.exe`, and attaches it to a GitHub Release.

Stable download URL for websites: `https://github.com/potato-robert/VLCouch/releases/latest/download/VLCouchSetup.exe`

The E2E settings spec reads `VERSION` automatically (`e2e/helpers/appVersion.ts`). If you add new version assertions in tests, use that helper rather than hardcoding the semver.

To test packaging locally (requires network for Python embeddable download):

```powershell
.\scripts\package.ps1
# Then, with Inno Setup 6 installed:
$version = (Get-Content VERSION -Raw).Trim()
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=$version install\VLCouch.iss
```

**Note:** The installer is unsigned in v1. Windows SmartScreen may warn on first run — code signing can be added later.

Installed users get update-available notifications in **Settings → About** when a newer GitHub Release exists. They download and run the new installer manually; library data in `%LOCALAPPDATA%\VLCouch\data` is preserved across upgrades.

## License

By contributing, you agree that your contributions are licensed under the project's GPL-3.0 license.
