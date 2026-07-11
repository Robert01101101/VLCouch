# VLCouch

A lean-back browser for local media files. Scans your movie and TV folders, organizes them into browseable rows, and hands off playback to VLC.

VLCouch is an independent, open-source project and is not affiliated with, endorsed by, or sponsored by VideoLAN or the VLC media player project.

**Windows-first** — VLC path detection, PowerShell scripts, and playback use the Windows VLC install. Other platforms are not supported yet.

## Requirements

- **Python 3** (backend)
- **Node.js** (frontend dev/build and tests)
- **[VLC](https://www.videolan.org/)** — auto-detected from the registry or `Program Files`; override with `VLC_PATH` in `.env`
- **[ffmpeg](https://ffmpeg.org/)** — on your PATH for thumbnails (or set `FFMPEG_PATH` in `.env`). Windows: `winget install ffmpeg`

## Quick start

1. Copy `.env.example` to `.env` and set `MEDIA_ROOTS` to your movie and TV folder paths.
2. Run the dev servers (creates a Python venv and installs npm deps on first run):
   ```powershell
   .\dev.ps1
   ```
3. Open http://localhost:5173
4. Click **Rescan Library** on the home page to import your files (scans do not run automatically unless `SCAN_ON_STARTUP=true`).

## Desktop shortcut (recommended)

One-time setup — builds the app and adds Desktop + Start menu shortcuts:

```powershell
.\scripts\install-shortcuts.ps1
```

Click **VLCouch** to start the server (if needed) and open your browser at http://127.0.0.1:8000. Bookmark that URL for quick access while the server is already running.

## Production (manual)

```powershell
cd frontend; npm run build; cd ..
backend\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

Then open http://localhost:8000

## Features

- Scans local movie/TV folders using `guessit` filename parsing
- **Hero banner** — suggests the next unwatched episode (or a movie to watch again)
- **Home page rows** — Recently Watched; top movie genres (from sidecar tag files); TV grouped by folder theme; movies grouped by decade
- **Search** — find movies and shows from the header search bar
- **Show detail** — seasons and episodes, up-next play, per-episode watched checkboxes
- **Thumbnails from your video files** (via ffmpeg) — generated lazily when you play or mark something watched; skips ~3 minutes past the start to avoid studio logos and title cards
- Optional Wikipedia plot summaries on detail pages (`METADATA_ENABLED=true`, text only, no API key)
- Poster-row browse UI with capped row length (`ROW_ITEM_LIMIT`)
- VLC playback with automatic subtitle detection (`.srt` / `.vtt` beside the video or in `Subs` folders)
- Manual watched tracking (playing an item marks it watched)

## Configuration

Settings live in `.env` at the repo root. See `.env.example` for all options:

| Variable | Purpose |
|----------|---------|
| `MEDIA_ROOTS` | JSON array of `{"path": "...", "type": "movies"\|"tv"}` roots |
| `METADATA_ENABLED` | `true` to fetch Wikipedia plot text on detail pages |
| `THUMBNAIL_SKIP_SECONDS` | Seconds into the file before grabbing a thumbnail frame (default `180`) |
| `ROW_ITEM_LIMIT` | Max posters per home-page row (default `30`) |
| `SCAN_LIMIT` | Max files scanned per root during limited scans (`0` = no limit) |
| `SCAN_ON_STARTUP` | `true` to scan when the server starts (default `false`) |
| `VLC_PATH` | Optional override for `vlc.exe` |
| `FFMPEG_PATH` | Optional override for `ffmpeg.exe` |

Test-specific overrides are documented in `.env.test.example`. Automated tests never use your real `MEDIA_ROOTS` or `library.db`.

## Movie genre tags (optional)

For extra home-page rows, add sidecar tag files next to each movie video:

```
Movie Folder/Title (Year) - Genre - Genre.txt
```

Examples: `1917 (2019) - Drama - War.txt`, `28 Days Later - Horror.nfo`. Tags are parsed on scan; the top five genres become browse rows. Torrent readme files (RARBG, YIFY, etc.) are ignored.

To inspect your library and preview genre counts:

```powershell
cd backend
python scripts/inventory_movies_folder.py
```

## Internet usage

**By default, fully offline.** The only optional online feature is Wikipedia text summaries when you open a show/movie detail page (`METADATA_ENABLED=true`). Thumbnails are always extracted locally from your video files — nothing is downloaded from the internet for images.

## Thumbnails

Thumbnails are generated when you play or mark an item as watched, using a frame from ~3 minutes in (or 30% of runtime, whichever is greater). Bump `THUMBNAIL_CACHE_VERSION` in `backend/app/thumbnails.py` when changing extraction settings to invalidate old cache files automatically on next startup.

Cached thumbnails and the library database are stored under `backend/data/` (gitignored).

## Testing with a large library

Set `SCAN_LIMIT` in `.env` to cap how many video files are processed **per media root** during dev smoke tests (e.g. `SCAN_LIMIT=50`). Production uses `0` (no limit). **Rescan Library** always scans the full library regardless of `SCAN_LIMIT`.

## Testing

```powershell
.\scripts\test.ps1              # full suite: API + unit + E2E
.\scripts\test.ps1 -Layer api   # backend pytest only
.\scripts\test.ps1 -Layer unit  # frontend Vitest only
.\scripts\test.ps1 -Layer e2e   # Playwright browser tests
```

See [AGENTS.md](AGENTS.md) for the agent verification workflow.

## License

GPL-3.0 — see [LICENSE](LICENSE).
