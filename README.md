<p align="center">
  <img src="docs/hero.jpg" alt="VLCouch — browse local movies and TV, play in VLC" width="720">
</p>

# VLCouch

**Browse local movies and TV like a streaming app — play them in VLC.**

Scans folders on your PC, builds poster rows and a hero banner, and launches [VLC](https://www.videolan.org/) when you hit Play. No accounts, cloud library, or transcoding. Offline by default.

> **Windows-first** — the installer, shortcuts, and folder picker are Windows-only. Linux and macOS can [run from source](#linux--macos). Not affiliated with VideoLAN or the VLC project.

## Features

- **Home** — hero (up next / watch again), browse rows, search
- **TV** — seasons, episodes, watch progress, binge playlists in VLC
- **Movies** — decade/genre rows; optional sidecar genre tags (see below)
- **Thumbnails** — extracted locally via ffmpeg (~3 min in); all-media backfill on by default
- **Settings** — media folders, rescan, thumbnail mode, VLC options, optional Wikipedia plots; install VLC/ffmpeg via winget on Windows

---

## Install

### Windows (recommended)

1. Download **VLCouchSetup-*.exe** from [GitHub Releases](https://github.com/Robert01101101/VLCouch/releases).
2. Launch **VLCouch** from the Start menu → add movie/TV folders → **Rescan Library**.

You also need [VLC](https://www.videolan.org/) (playback) and [ffmpeg](https://ffmpeg.org/) (thumbnails). On Windows, **Settings** shows their status and offers **Install (winget)** when available, or a download link otherwise.

The installer bundles Python and the app. Library data lives in `%LOCALAPPDATA%\VLCouch\data\` and is preserved across upgrades. Bookmark http://127.0.0.1:8000. **Settings → About** checks for newer releases.

### Windows (from source)

```powershell
.\Setup.bat   # or .\scripts\install-shortcuts.ps1
```

Installs dependencies, builds the frontend, and creates a Desktop shortcut. Data in `backend/data/`.

### Linux & macOS

Unofficial — no installer. Requires **Python 3.12+**, **Node 20+**, VLC, and ffmpeg:

```bash
git clone https://github.com/Robert01101101/VLCouch.git && cd VLCouch
cp docs/.env.example .env
python3 -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

Open http://127.0.0.1:8000 → **Settings** → **Rescan Library**. Type folder paths manually (no native picker). Set `VLC_PATH` / `FFMPEG_PATH` in `.env` if not on `PATH`.

### Development

```powershell
copy docs\.env.example .env   # optional MEDIA_ROOTS
.\scripts\dev.ps1               # backend :8000, frontend :5173
```

---

## Configuration

Runtime toggles live in **Settings** (saved in the database — no restart). `.env` sets first-run defaults; see [`docs/.env.example`](docs/.env.example).

| Variable | Purpose |
|----------|---------|
| `MEDIA_ROOTS` | Initial folders (JSON array); then managed in Settings |
| `VLC_PATH` / `FFMPEG_PATH` | Override auto-detection |
| `SCAN_ON_STARTUP` | Auto-rescan when the server starts |
| `THUMBNAIL_SKIP_SECONDS` | Seconds before frame grab (default `180`) |
| `SCAN_LIMIT` | Cap files per root for manual scan scripts only (`0` = no limit) |

**Movie genre rows** — add a sidecar file next to the video, e.g. `1917 (2019) - Drama - War.txt`. Torrent readme files are ignored.

---

## Developers

```powershell
.\scripts\test.ps1              # full suite
.\scripts\test.ps1 -Layer api   # backend pytest
.\scripts\test.ps1 -Layer unit  # frontend Vitest
.\scripts\test.ps1 -Layer e2e   # Playwright
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for PR guidelines (including Windows installer releases) and [AGENTS.md](AGENTS.md) for architecture. API docs: http://localhost:8000/docs.

## License

GPL-3.0 — see [LICENSE](LICENSE).
