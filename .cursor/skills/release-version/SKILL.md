---
name: release-version
description: >-
  Cut a new VLCouch Windows release — bump VERSION, verify tests and packaging,
  tag vX.Y.Z, and publish VLCouchSetup.exe via GitHub Actions. Use when the
  user asks to release, ship, publish, or tag a new version.
---

# Release a new version

End-user releases are **tag-driven**: push `vX.Y.Z` and [`.github/workflows/release.yml`](.github/workflows/release.yml) builds `VLCouchSetup-{version}.exe` and attaches it to a GitHub Release.

## When to use

- User asks to release, ship, publish, or tag a new version
- User wants to cut a Windows installer release
- User asks how to bump the version and publish to GitHub Releases

## Prerequisites

- Changes are merged or ready on the branch you will tag (usually `main`)
- `git status` is clean (no uncommitted work unless the version bump is the only pending change)
- Remote is `origin` and you can push tags
- **Do not** commit `.env`, `backend/data/`, or user media

## Version source of truth

| File | Role |
|------|------|
| [`VERSION`](VERSION) | Single source — must match the git tag (without `v` prefix) |
| [`backend/app/version.py`](backend/app/version.py) | Runtime loader (reads `version.txt` when packaged, else `VERSION`) |
| Tag format | `v0.2.0` → `VERSION` contains `0.2.0` |

CI **fails** if the tag and `VERSION` disagree.

## Release checklist

Copy and track progress:

```
Release v____:
- [ ] 1. Run full test suite
- [ ] 2. Bump VERSION
- [ ] 3. (Recommended) Local package smoke test
- [ ] 4. Commit version bump
- [ ] 5. Push to main
- [ ] 6. Create and push tag vX.Y.Z
- [ ] 7. Confirm GitHub Actions release job succeeded
- [ ] 8. Confirm GitHub Release has VLCouchSetup-X.Y.Z.exe
```

## Step-by-step

### 1. Verify tests

From repo root:

```powershell
.\scripts\test.ps1 -Layer all
```

Fix failures before releasing. At minimum run layers touched since the last release.

### 2. Bump VERSION

Edit [`VERSION`](VERSION) — one line, semver `MAJOR.MINOR.PATCH` (e.g. `0.2.0`).

No other files need manual version edits; packaging copies `VERSION` into `backend/app/version.txt`.

### 3. Local package smoke test (recommended)

Requires network (downloads Python embeddable). Optional Inno Setup for full installer build.

```powershell
.\scripts\package.ps1
```

This builds `dist/staging/`, installs embeddable Python + pip deps, and smoke-starts the server on port 8010.

To build the installer locally (Inno Setup 6 required):

```powershell
$version = (Get-Content VERSION -Raw).Trim()
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=$version install\VLCouch.iss
# Output: dist/installer/VLCouchSetup-{version}.exe
```

`dist/` is gitignored — do not commit it.

### 4. Commit the version bump

Only when the user asked you to commit. Use the **generate-commit-message** skill:

```powershell
git add VERSION
git commit -m "$(cat <<'EOF'
chore(release): bump version to X.Y.Z

EOF
)"
```

### 5. Push to main

```powershell
git push origin main
```

### 6. Tag and push

Replace `X.Y.Z` with the value in `VERSION`:

```powershell
$version = (Get-Content VERSION -Raw).Trim()
git tag "v$version"
git push origin "v$version"
```

Or in one step after verifying `$version`:

```powershell
git tag v0.2.0
git push origin v0.2.0
```

**Rules:**

- Tag must start with `v`
- Tag body (after `v`) must exactly match `VERSION`
- Do not move or delete published tags without explicit user request

### 7. Monitor CI

```powershell
gh run list --workflow=release.yml --limit 3
gh run watch
```

Or open the Actions tab on GitHub. The **Release** workflow runs on `windows-latest` and:

1. Validates tag vs `VERSION`
2. Runs `.\scripts\package.ps1`
3. Installs Inno Setup via Chocolatey
4. Compiles `install/VLCouch.iss`
5. Creates a GitHub Release with `VLCouchSetup-{version}.exe`

### 8. Post-release verification

```powershell
$version = (Get-Content VERSION -Raw).Trim()
gh release view "v$version"
```

Confirm:

- Release exists with auto-generated notes
- Asset `VLCouchSetup-{version}.exe` is attached
- Installed users will see **Settings → About → Update available** when their version is older (background check against GitHub Releases API)

## What gets published

| Artifact | Path on user machine after install |
|----------|-----------------------------------|
| `VLCouchSetup-X.Y.Z.exe` | Installs to `%LOCALAPPDATA%\VLCouch\app\` |
| User data (preserved) | `%LOCALAPPDATA%\VLCouch\data\` |

Dev/git installs (`.\scripts\dev.ps1`, `Setup.bat`) are unaffected.

## Troubleshooting

| Failure | Action |
|---------|--------|
| `Tag version X does not match VERSION file` | Align `VERSION` and tag, push fix, delete/recreate tag only if release not published |
| `package.ps1` smoke test timeout | Check port 8010 not in use; re-run package script |
| Inno compile fails in CI | Inspect workflow log; verify `dist/staging/` layout locally |
| SmartScreen warning for users | Expected — installer is unsigned in v1 (see CONTRIBUTING) |
| Update check not showing | Requires a published GitHub Release with `VLCouchSetup-*.exe` asset; skipped in test/dev mode |

## Do not

- Bump `frontend/package.json` version for releases (not used at runtime)
- Commit `dist/`, `backend/data/`, or `.env`
- Force-push tags or rewrite published release history without user approval
- Sign the installer unless the user has set up code signing

## Related

- Human docs: [CONTRIBUTING.md](CONTRIBUTING.md) — Releasing a Windows installer
- Packaging: [`scripts/package.ps1`](scripts/package.ps1), [`install/VLCouch.iss`](install/VLCouch.iss)
- Update notifications: [`backend/app/update_check.py`](backend/app/update_check.py)
