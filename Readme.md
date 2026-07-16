# VLCouch

**Browse your local movies and TV like a streaming app — play them in VLC.**

VLCouch scans folders on your PC, builds poster rows and a “what to watch next” hero, and launches [VLC](https://www.videolan.org/) when you hit Play. No accounts, no cloud library, no transcoding. Your files stay on your drives.

> **Windows-first** — built for Windows (PowerShell, VLC registry detection). Other platforms are not supported yet.  
> VLCouch is independent open source and is not affiliated with VideoLAN or the VLC project.

---

## Why use it?

If you keep movies and TV on external drives or a NAS mount, you already have the hard part — the files. VLCouch adds the couch experience:

- **Lean-back browsing** — poster rows, search, show seasons, and a hero banner for “continue watching” or “watch again”
- **Stays local** — offline by default; thumbnails come from your own video files, not the internet
- **VLC playback** — full codec support and subtitle auto-detection (`.srt` / `.vtt` beside the file or in `Subs` folders)
- **Simple watch tracking** — playing marks an item watched; TV cards show progress across episodes
- **Your folders, your rules** — point at any movie/TV roots; rescan when you add new files

---

## How to use it

1. **Install** — Python 3, Node.js, [VLC](https://www.videolan.org/), and [ffmpeg](https://ffmpeg.org/) (`winget install ffmpeg` on Windows).
2. **Run setup** — double-click `Setup.bat` (or `.\scripts\install-shortcuts.ps1`) to install dependencies and create shortcuts.
3. **Launch** — click the **VLCouch** Desktop shortcut; your browser opens automatically.
4. **Add folders** — on first launch, use the setup screen to browse for your movie and TV folders (or add them later in **Settings**).
5. **Import** — click **Scan library** (or **Settings** → **Rescan Library**) to import your files.
6. **Browse & play** — pick from the home rows or search bar; VLC opens the file.

For day-to-day use after setup, bookmark http://127.0.0.1:8000. The server remembers watch history, media folders, and thumbnails under `backend/data/`. Optional `.env` values still work as defaults on first run — see [Configuration](#configuration).

---

## Features

| | |
|---|---|
| **Home** | Hero (up next / watch again), Recently Watched, TV by folder theme, movies by decade, top genres |
| **Shows** | Seasons, episodes, up-next play, per-episode and season watched toggles |
| **Search** | Movies and shows from the header bar |
| **Settings** | Rescan, scan-on-startup, thumbnail mode, optional Wikipedia plot summaries |
| **Thumbnails** | Extracted locally via ffmpeg (~3 min in, past logos); all-media backfill on by default |
| **Privacy** | Fully offline unless you enable Wikipedia text on show pages |

Optional **genre rows** for movies: add sidecar tag files like `1917 (2019) - Drama - War.txt` next to the video — see [Movie genre tags](#movie-genre-tags) below.

---

## Get started

### Development

```powershell
# 1. Configure media paths
copy .env.example .env
# Edit MEDIA_ROOTS in .env

# 2. Start backend + frontend (creates venv and installs deps on first run)
.\dev.ps1
```

Open http://localhost:5173 → **Settings** → **Rescan Library**.

Scans do not run on startup unless you enable **Automatically rescan on startup** in Settings (or `SCAN_ON_STARTUP=true` in `.env`).

### Desktop shortcut (recommended)

One-time setup — installs dependencies, builds the frontend, and adds Desktop + Start menu shortcuts:

```powershell
.\Setup.bat
```

Or from PowerShell: `.\scripts\install-shortcuts.ps1`

Click **VLCouch** to start the server and open http://127.0.0.1:8000. Add your media folders in the app (first-run wizard or **Settings**).

### Production (manual)

```powershell
cd frontend; npm run build; cd ..
backend\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

Then open http://localhost:8000.

---

## Configuration

### Settings page

Runtime toggles (saved in `backend/data/library.db` — no restart needed):

| Toggle | What it does |
|--------|----------------|
| **Media folders** | Add or remove movie and TV library paths (saved in the app database) |
| **Rescan Library** | Full scan of all configured media folders |
| **Automatically rescan on startup** | Scan when the server starts |
| **Generate thumbnails for all media** | Background posters for the whole library (default on). Off = thumbnails on play/mark-watched only |
| **Wikipedia plot summaries** | Fetch plot text on show detail pages |

### Environment (`.env`)

Requires a server restart. See `.env.example` for defaults.

| Variable | Purpose |
|----------|---------|
| `MEDIA_ROOTS` | Initial media folders on first run only (JSON array). After that, folders are managed in **Settings** |
| `METADATA_ENABLED` | Initial default for Wikipedia summaries |
| `SCAN_ON_STARTUP` | Initial default for startup scans |
| `THUMBNAIL_SKIP_SECONDS` | Seconds before thumbnail frame grab (default `180`) |
| `ROW_ITEM_LIMIT` | Max posters per home row (default `30`) |
| `SCAN_LIMIT` | Cap files per root for manual scan scripts only (`0` = no limit). Server rescan ignores this |
| `VLC_PATH` | Override path to `vlc.exe` |
| `FFMPEG_PATH` | Override path to `ffmpeg.exe` |

---

## Movie genre tags

Add a small text file next to a movie to tag genres — the top five become home-page rows:

```
Movie Folder/Title (Year) - Drama - War.txt
Movie Folder/28 Days Later - Horror.nfo
```

Torrent readme files (RARBG, YIFY, etc.) are ignored. Preview counts:

```powershell
cd backend
python scripts/inventory_movies_folder.py
```

---

## Thumbnails & privacy

- **Thumbnails** — ffmpeg grabs a frame from your video (~3 minutes in, or 30% of runtime). Cached under `backend/data/posters/`.
- **All-media mode** (Settings, default on) backfills posters on startup and after rescan. Turn off for on-demand only.
- **Offline** — no network use unless Wikipedia summaries are enabled. No API keys, no TMDB, no image downloads.

Developers: bump `THUMBNAIL_CACHE_VERSION` in `backend/app/thumbnails.py` to invalidate old cache after changing extraction settings.

---

## Large libraries

Use `SCAN_LIMIT=50` in `.env` when running manual scan scripts (`cd backend; python scripts/smoke_scan.py`) for a quick smoke test. The live server and **Rescan Library** always scan everything.

---

## For developers

```powershell
.\scripts\test.ps1              # full suite
.\scripts\test.ps1 -Layer api   # backend pytest
.\scripts\test.ps1 -Layer unit  # frontend Vitest
.\scripts\test.ps1 -Layer e2e   # Playwright
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for PR guidelines and [AGENTS.md](AGENTS.md) for architecture and file map. API docs: http://localhost:8000/docs when the backend is running.

---

## License

GPL-3.0 — see [LICENSE](LICENSE).
