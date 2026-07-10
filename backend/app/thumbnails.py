import hashlib
import logging
import shutil
import subprocess
from pathlib import Path

from app.config import FFMPEG_PATH, POSTERS_DIR, THUMBNAIL_SKIP_SECONDS

logger = logging.getLogger(__name__)

# Bump when seek logic, ffmpeg params, or cache layout changes to invalidate old thumbnails.
THUMBNAIL_CACHE_VERSION = 2
_CACHE_VERSION_FILE = ".cache_version"


def is_current_cache_path(path: str | Path) -> bool:
    name = Path(path).name
    return f"_v{THUMBNAIL_CACHE_VERSION}_" in name


def is_valid_poster_path(path: str | Path | None) -> bool:
    if not path:
        return False
    poster = Path(path)
    return poster.exists() and is_current_cache_path(poster)


def needs_poster_regeneration(poster_path: str | Path | None) -> bool:
    return not is_valid_poster_path(poster_path)


def poster_public_url(poster_path: str | Path | None) -> str | None:
    if not is_valid_poster_path(poster_path):
        return None
    return f"/posters/{Path(poster_path).name}"


def reconcile_stale_poster_paths() -> int:
    """Clear DB poster_path values that are missing or from an old cache version."""
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Movie, Show

    cleared = 0
    with Session(engine) as session:
        changed = False
        for movie in session.exec(select(Movie)).all():
            if movie.poster_path and not is_valid_poster_path(movie.poster_path):
                movie.poster_path = None
                session.add(movie)
                changed = True
                cleared += 1
        for show in session.exec(select(Show)).all():
            if show.poster_path and not is_valid_poster_path(show.poster_path):
                show.poster_path = None
                session.add(show)
                changed = True
                cleared += 1
        if changed:
            session.commit()
    if cleared:
        logger.info("Cleared %d stale poster path(s) from the database", cleared)
    return cleared


def ensure_thumbnail_cache_current() -> bool:
    """Drop stale thumbnail files and DB poster paths when cache version changes."""
    version_file = POSTERS_DIR / _CACHE_VERSION_FILE
    current = str(THUMBNAIL_CACHE_VERSION)
    stored = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else None
    if stored == current:
        return False

    removed = 0
    for path in POSTERS_DIR.glob("*.jpg"):
        path.unlink(missing_ok=True)
        removed += 1

    _clear_poster_paths_in_db()
    version_file.write_text(current, encoding="utf-8")
    logger.info(
        "Thumbnail cache upgraded to v%s (%d files removed, poster paths cleared)",
        current,
        removed,
    )
    reconcile_stale_poster_paths()
    return True


def ensure_thumbnail_cache_current_on_startup() -> None:
    """Run cache-version migration and sweep stale DB poster paths on every startup."""
    ensure_thumbnail_cache_current()
    reconcile_stale_poster_paths()


def _clear_poster_paths_in_db() -> None:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Movie, Show

    with Session(engine) as session:
        changed = False
        for movie in session.exec(select(Movie)).all():
            if movie.poster_path:
                movie.poster_path = None
                session.add(movie)
                changed = True
        for show in session.exec(select(Show)).all():
            if show.poster_path:
                show.poster_path = None
                session.add(show)
                changed = True
        if changed:
            session.commit()


def _find_ffmpeg() -> str | None:
    if FFMPEG_PATH and Path(FFMPEG_PATH).exists():
        return FFMPEG_PATH
    return shutil.which("ffmpeg")


def _find_ffprobe() -> str | None:
    if FFMPEG_PATH:
        probe = Path(FFMPEG_PATH).parent / "ffprobe.exe"
        if probe.exists():
            return str(probe)
    return shutil.which("ffprobe")


def _video_duration_seconds(video_path: Path) -> float | None:
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.debug("ffprobe failed for %s: %s", video_path, e)
    return None


def _pick_seek_seconds(duration: float | None) -> float:
    """Seek past studio logos — into the actual content."""
    minimum = float(THUMBNAIL_SKIP_SECONDS)
    if not duration or duration <= 0:
        return minimum
    # Use the larger of fixed skip or 30% into the video
    candidate = max(minimum, duration * 0.30)
    # Stay at least 30s from the end on short content
    return min(candidate, max(0.0, duration - 30.0))


def _cache_path(video_path: Path, cache_key: str) -> Path:
    digest = hashlib.md5(str(video_path).encode(), usedforsecurity=False).hexdigest()[:10]
    return POSTERS_DIR / f"{cache_key}_v{THUMBNAIL_CACHE_VERSION}_{digest}.jpg"


def cached_thumbnail_path(video_path: str | Path, cache_key: str) -> str | None:
    """Return cached frame path if it already exists for the current cache version."""
    output = _cache_path(Path(video_path), cache_key)
    if output.exists() and is_current_cache_path(output):
        return str(output)
    return None


def get_or_extract_thumbnail(video_path: str | Path, cache_key: str) -> str | None:
    """Return cached frame path, extracting from video if needed."""
    cached = cached_thumbnail_path(video_path, cache_key)
    if cached:
        return cached
    return extract_thumbnail(video_path, cache_key)


def extract_thumbnail(video_path: str | Path, cache_key: str) -> str | None:
    """Extract a single frame from a video file. Returns local path or None."""
    ffmpeg = _find_ffmpeg()
    path = Path(video_path)
    if not ffmpeg or not path.exists():
        return None

    output = _cache_path(path, cache_key)
    if output.exists() and is_current_cache_path(output):
        return str(output)

    duration = _video_duration_seconds(path)
    seek = _pick_seek_seconds(duration)

    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(seek),
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                "-y",
                str(output),
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            logger.info("Thumbnail saved: %s (seek %.0fs)", output.name, seek)
            return str(output)
        logger.debug("ffmpeg thumbnail failed for %s: %s", path, result.stderr.decode()[:200])
    except Exception as e:
        logger.debug("Thumbnail extraction error for %s: %s", path, e)
    return None


def ffmpeg_available() -> bool:
    return _find_ffmpeg() is not None
