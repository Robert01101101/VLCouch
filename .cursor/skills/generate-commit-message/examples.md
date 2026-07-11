# Commit message examples

Each example shows a diff summary (input) and the recommended message (output).

---

## Bug fix

**Input:** `watch_service.py` — `get_status` returned `position: null` when a row existed; frontend always showed "Play" instead of "Resume".

**Output:**

```
fix(watch): return saved position from watch status API

The UI could not offer resume because the status endpoint dropped the
stored offset even when watch history existed.

Changes:
- Include position_seconds in watch status response
- Align response shape with frontend api.js expectations
```

---

## New feature

**Input:** New `HeroBanner` on home, `PosterCard` progress bar, API field `watch_progress_percent`.

**Output:**

```
feat(home): show watch progress on poster cards and hero

Viewers can see at a glance how far they are into a title before opening it.

Changes:
- Add progress overlay to PosterCard when watch data exists
- Surface featured in-progress title in HeroBanner
- Expose watch_progress_percent from library browse API
```

---

## Refactor (no behavior change)

**Input:** Extracted duplicate VLC launch logic from two routers into `watch_service.py`.

**Output:**

```
refactor(watch): centralize VLC launch in watch service

Reduces duplication and keeps playback flags consistent across entry points.

Changes:
- Move subprocess launch helpers into watch_service
- Call shared helper from play and resume routes
```

---

## Tests only

**Input:** Added `test_watch_api.py` cases for resume; no production code change.

**Output:**

```
test(watch): cover resume position in watch API

Changes:
- Assert status returns position when history exists
- Assert play endpoint receives start offset in TEST_MODE
```

---

## Documentation

**Input:** Updated Readme with shortcut install steps and `start.ps1` usage.

**Output:**

```
docs: document Windows shortcuts and startup scripts

Changes:
- Describe install-shortcuts.ps1 and desktop launcher flow
- Clarify dev vs production start commands in Readme
```

---

## Chore / tooling

**Input:** `install-shortcuts.ps1` creates VLCouch.lnk; `start.ps1` opens browser after backend is up.

**Output:**

```
chore(scripts): improve one-click Windows launch experience

Changes:
- Add desktop shortcut installer for VLCouch.lnk
- Wait for health check before opening the browser in start.ps1
```

---

## Breaking change

**Input:** Renamed API field `progress` → `position_seconds`; updated frontend.

**Output:**

```
fix(watch)!: rename progress field to position_seconds

The old name collided with library scan progress and confused clients.

Changes:
- Rename field in watch status and continue-watching responses
- Update frontend api.js and ShowDetail consumers

Breaking change: clients using `progress` must switch to `position_seconds`.
```

---

## Too large — suggest split

**Input:** Same diff adds watch API, redesigns ShowDetail, and fixes unrelated poster cache bug.

**Output (guidance, not one commit):**

Suggest three commits:

1. `fix(posters): refresh stale episode poster cache after scan`
2. `feat(watch): add resume position to watch API and playback`
3. `feat(shows): redesign show detail with continue-watching section`
