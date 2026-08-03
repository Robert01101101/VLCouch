---
name: release-version
description: >-
  Bump VERSION, sync E2E version checks, run the full test suite, and commit only
  if green — then tag and publish VLCouchSetup.exe. ALWAYS use this skill when
  the user mentions version, release, bump, semver, tag, ship, publish, next
  version, prepare release, or cutting a release — even vague one-line prompts.
---

# Release a new version

**Read this entire skill before doing anything** when the request touches versioning or releases.

End-user releases are **tag-driven**: push `vX.Y.Z` and [`.github/workflows/release.yml`](.github/workflows/release.yml) builds `VLCouchSetup.exe` and attaches it to a GitHub Release.

**Stable download URL** (for websites — always serves the latest release):

`https://github.com/potato-robert/VLCouch/releases/latest/download/VLCouchSetup.exe`

## Trigger phrases (use this skill)

Load this skill immediately if the user says anything like:

- "bump the version" / "bump to next release"
- "prepare for release" / "ready to ship"
- "cut a release" / "tag a release"
- "what's the next version" (then follow bump workflow if they want it done)
- "commit the version bump"
- "release" / "publish" / "ship" (when context is VLCouch versioning)

Do **not** edit `VERSION` or create a version commit without following the **mandatory workflow** below.

## CI on pull requests

[`.github/workflows/test.yml`](.github/workflows/test.yml) runs a **single** check on every PR and push to `main`/`master`:

1. **Ruff** — `python -m ruff check backend/app backend/tests`
2. **Full test suite** — `.\scripts\test.ps1 -Layer all` (api + unit + e2e)

Tag pushes do **not** run this workflow; they trigger [`.github/workflows/release.yml`](.github/workflows/release.yml) (installer build only). Run the full suite locally before tagging — CI on the merged PR is the gate.

## Mandatory workflow (version bump + commit)

Use this order every time. **Do not commit until step 4 passes.**

```
1. Bump VERSION
2. Sync E2E version spec (verify, fix if needed)
3. Run full test suite locally (.\scripts\test.ps1 -Layer all) — same as PR CI
4. Commit version bump ONLY if all tests passed
```

If step 3 fails: fix the code or **revert the VERSION change** — never commit a failed bump.

If the user only asked to bump (not tag/push), stop after step 4.

### Step 1 — Bump VERSION

1. Read the current value:
   ```powershell
   Get-Content VERSION
   ```
2. Choose the next semver (`MAJOR.MINOR.PATCH`). Default guidance:
   - **Patch** (`0.2.0` → `0.2.1`): bug fixes only
   - **Minor** (`0.2.0` → `0.3.0`): new features or notable polish
   - **Major**: breaking changes (rare pre-1.0)
3. If unclear which bump level the user wants, ask before editing.
4. Edit [`VERSION`](VERSION) — single line, no `v` prefix.

No other runtime files need manual edits for a normal bump; packaging copies `VERSION` into `backend/app/version.txt` at build time.

### Step 2 — Sync E2E version spec

E2E must track the bumped `VERSION` without hardcoding semver literals.

1. Confirm [`e2e/specs/settings.spec.ts`](e2e/specs/settings.spec.ts) uses the helper:
   ```typescript
   import { appVersion, versionPattern } from '../helpers/appVersion'
   const version = appVersion()
   // ...
   await expect(page.getByTestId('settings-version')).toHaveText(versionPattern(version))
   ```
2. If the spec hardcodes a version (e.g. `/0\.2\.0/`), replace it with `appVersion()` / `versionPattern()` from [`e2e/helpers/appVersion.ts`](e2e/helpers/appVersion.ts).
3. Grep E2E for stray hardcoded app versions:
   ```powershell
   rg '0\.\d+\.\d+' e2e/specs/
   ```
   Matches in `settings.spec.ts` for version assertions are a smell — use the helper instead.

After a correct setup, bumping `VERSION` alone updates what E2E expects. No separate "e2e version bump" file edit is needed unless the spec regressed to hardcoded strings.

### Step 3 — Run the complete test suite

From repo root (required before any version commit). This matches what PR CI runs in `test.yml` (ruff + full suite):

```powershell
python -m ruff check backend/app backend/tests --config backend/pyproject.toml
.\scripts\test.ps1 -Layer all
```

All layers must pass: **ruff**, **api**, **unit**, and **e2e**.

If anything fails, fix failures and re-run from step 3. Do not commit the version bump while red.

### Step 4 — Commit (only after green tests)

Only when the user asked you to commit. Use the **generate-commit-message** skill on the `VERSION` change.

```powershell
git add VERSION
# Include e2e/specs or e2e/helpers only if you changed them in step 2
git commit -m "chore(release): bump version to X.Y.Z"
```

**Never** commit a version bump without a passing full suite in the same session.

---

## Full release checklist (bump + tag + publish)

Use after the mandatory workflow above when the user wants a published release:

```
Release v____:
- [ ] 1. Bump VERSION (workflow step 1)
- [ ] 2. Sync E2E version spec (workflow step 2)
- [ ] 3. Run ruff + full test suite — all green (workflow step 3; same as PR CI)
- [ ] 4. Commit version bump (workflow step 4)
- [ ] 5. (Recommended) Local package smoke test
- [ ] 6. Push to main (or merge PR first)
- [ ] 7. Create and push tag vX.Y.Z
- [ ] 8. Confirm GitHub Actions release job succeeded
- [ ] 9. Confirm GitHub Release has VLCouchSetup.exe
```

## Prerequisites (tag + publish)

- Feature work is merged or ready on the branch you will tag (usually `main`)
- `git status` is clean after the version commit (or version bump is the only pending change before commit)
- Remote is `origin` and you can push tags
- **Do not** commit `.env`, `backend/data/`, or user media

## Version source of truth

| File | Role |
|------|------|
| [`VERSION`](VERSION) | Single source — must match the git tag (without `v` prefix) |
| [`backend/app/version.py`](backend/app/version.py) | Runtime loader (reads `version.txt` when packaged, else `VERSION`) |
| [`e2e/helpers/appVersion.ts`](e2e/helpers/appVersion.ts) | E2E reads `VERSION` at test runtime |
| [`e2e/specs/settings.spec.ts`](e2e/specs/settings.spec.ts) | Settings page version assertion (must use helper, not hardcoded semver) |
| Tag format | `v0.3.0` → `VERSION` contains `0.3.0` |

CI **fails** if the tag and `VERSION` disagree.

Unit tests may use arbitrary semver fixtures (e.g. `0.1.0` vs `0.2.0` in update-check mocks) — those are not the app version and do not need bumping.

## Local package smoke test (recommended before tag)

Requires network (downloads Python embeddable). Optional Inno Setup for full installer build.

```powershell
.\scripts\package.ps1
```

```powershell
$version = (Get-Content VERSION -Raw).Trim()
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=$version install\VLCouch.iss
# Output: dist/installer/VLCouchSetup.exe
```

`dist/` is gitignored — do not commit it.

## Tag and push

Replace `X.Y.Z` with the value in `VERSION`:

```powershell
$version = (Get-Content VERSION -Raw).Trim()
git tag "v$version"
git push origin "v$version"
```

**Rules:**

- Tag must start with `v`
- Tag body (after `v`) must exactly match `VERSION`
- Do not move or delete published tags without explicit user request

## Monitor CI and verify release

```powershell
gh run list --workflow=release.yml --limit 3
gh run watch
$version = (Get-Content VERSION -Raw).Trim()
gh release view "v$version"
```

Confirm:

- Release exists with auto-generated notes
- Asset `VLCouchSetup.exe` is attached
- Stable URL resolves: `.../releases/latest/download/VLCouchSetup.exe`
- Installed users will see **Settings → About → Update available** when their version is older

## What gets published

| Artifact | Path on user machine after install |
|----------|-----------------------------------|
| `VLCouchSetup.exe` | Installs to `%LOCALAPPDATA%\VLCouch\app\` (version in tag + in-app About) |
| User data (preserved) | `%LOCALAPPDATA%\VLCouch\data\` |

## Troubleshooting

| Failure | Action |
|---------|--------|
| E2E settings version assertion fails after bump | Ensure `settings.spec.ts` uses `appVersion()` — not a hardcoded semver |
| Full suite fails after bump | Fix code or revert `VERSION`; do not commit the bump |
| `Tag version X does not match VERSION file` | Align `VERSION` and tag; delete/recreate tag only if release not published |
| `package.ps1` smoke test timeout | Check port 8010 not in use; re-run package script |
| Update check not showing | Requires a published GitHub Release with `VLCouchSetup.exe` asset |

## Do not

- Bump `frontend/package.json` version for releases (not used at runtime)
- Commit `VERSION` before `.\scripts\test.ps1 -Layer all` passes
- Hardcode semver in `e2e/specs/` — use `e2e/helpers/appVersion.ts`
- Commit `dist/`, `backend/data/`, or `.env`
- Force-push tags without user approval

## Related

- Commit messages: **generate-commit-message** skill
- Human docs: [CONTRIBUTING.md](CONTRIBUTING.md)
- Packaging: [`scripts/package.ps1`](scripts/package.ps1), [`install/VLCouch.iss`](install/VLCouch.iss)
- Update notifications: [`backend/app/update_check.py`](backend/app/update_check.py)
