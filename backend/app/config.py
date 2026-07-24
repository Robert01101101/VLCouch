import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Load .env from project root regardless of working directory
load_dotenv(PROJECT_ROOT / ".env")

APP_ENV = os.getenv("APP_ENV", "production")
IS_TEST = APP_ENV == "test"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() in ("1", "true", "yes")

if IS_TEST:
    _test_tmp = BASE_DIR / "tests" / ".tmp"
    _test_tmp.mkdir(parents=True, exist_ok=True)
    DATA_DIR = Path(os.getenv("TEST_DB_PATH", _test_tmp / "library.db")).parent
    DB_PATH = Path(os.getenv("TEST_DB_PATH", _test_tmp / "library.db"))
    POSTERS_DIR = Path(os.getenv("TEST_POSTERS_DIR", _test_tmp / "posters"))
else:
    _data_override = os.getenv("VLCOUCH_DATA_DIR")
    DATA_DIR = Path(_data_override) if _data_override else BASE_DIR / "data"
    DB_PATH = DATA_DIR / "library.db"
    POSTERS_DIR = DATA_DIR / "posters"

DATA_DIR.mkdir(parents=True, exist_ok=True)
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")  # deprecated, unused
VLC_PATH = os.getenv("VLC_PATH", "")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")

if IS_TEST:
    METADATA_ENABLED = False
else:
    METADATA_ENABLED = os.getenv("METADATA_ENABLED", "false").lower() in ("1", "true", "yes")

_thumbnail_skip = os.getenv("THUMBNAIL_SKIP_SECONDS", "180")
THUMBNAIL_SKIP_SECONDS = int(_thumbnail_skip) if _thumbnail_skip.isdigit() else 180

_row_limit = os.getenv("ROW_ITEM_LIMIT", "30")
ROW_ITEM_LIMIT = int(_row_limit) if _row_limit.isdigit() else 30

_scan_limit = os.getenv("SCAN_LIMIT", "0")
SCAN_LIMIT = int(_scan_limit) if _scan_limit.isdigit() else 0

if IS_TEST:
    SCAN_ON_STARTUP = os.getenv("SCAN_ON_STARTUP", "false").lower() in ("1", "true", "yes")
else:
    SCAN_ON_STARTUP = os.getenv("SCAN_ON_STARTUP", "false").lower() in ("1", "true", "yes")

_vlc_port_base = os.getenv("VLC_HTTP_PORT_BASE", "9080")
VLC_HTTP_PORT_BASE = int(_vlc_port_base) if _vlc_port_base.isdigit() else 9080
_vlc_port_max = os.getenv("VLC_HTTP_PORT_MAX", "9099")
VLC_HTTP_PORT_MAX = int(_vlc_port_max) if _vlc_port_max.isdigit() else 9099

_poll_interval = os.getenv("PLAYBACK_POLL_INTERVAL_SECONDS", "5")
PLAYBACK_POLL_INTERVAL_SECONDS = int(_poll_interval) if _poll_interval.isdigit() else 5

_completion_ratio = os.getenv("PLAYBACK_COMPLETION_RATIO", "0.90")
try:
    PLAYBACK_COMPLETION_RATIO = float(_completion_ratio)
except ValueError:
    PLAYBACK_COMPLETION_RATIO = 0.90

_min_resume = os.getenv("PLAYBACK_MIN_RESUME_SECONDS", "30")
PLAYBACK_MIN_RESUME_SECONDS = int(_min_resume) if _min_resume.isdigit() else 30

_end_seconds = os.getenv("PLAYBACK_END_SECONDS", "30")
PLAYBACK_END_SECONDS = int(_end_seconds) if _end_seconds.isdigit() else 30

PLAYLISTS_DIR = DATA_DIR / "playlists"
PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_media_roots() -> list[dict]:
    if IS_TEST:
        if os.getenv("TEST_MEDIA_ROOTS"):
            try:
                return json.loads(os.getenv("TEST_MEDIA_ROOTS", "[]"))
            except json.JSONDecodeError:
                pass
        fixture_media = BASE_DIR / "tests" / "fixtures" / "media"
        return [
            {"path": str(fixture_media / "movies"), "type": "movies"},
            {"path": str(fixture_media / "tv"), "type": "tv"},
        ]
    raw = os.getenv("MEDIA_ROOTS", "[]")
    try:
        roots = json.loads(raw)
        if isinstance(roots, list):
            return roots
    except json.JSONDecodeError:
        pass
    return []


MEDIA_ROOTS = _load_media_roots()

FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
