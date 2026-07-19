import json

from sqlalchemy import func
from sqlmodel import Session, select

from app.config import MEDIA_ROOTS, METADATA_ENABLED, SCAN_ON_STARTUP
from app.dependencies import DEPENDENCIES, winget_available
from app.models import AppSetting, Episode, Movie, Show
from app.thumbnails import ffmpeg_available
from app.vlc import find_vlc_path

APP_VERSION = "0.1.0"
GITHUB_URL = "https://github.com/Robert01101101/VLCouch"

KEY_METADATA_ENABLED = "metadata_enabled"
KEY_SCAN_ON_STARTUP = "scan_on_startup"
KEY_AUTO_GENERATE_THUMBNAILS = "auto_generate_thumbnails"
KEY_SIMPLE_VLC_PLAYBACK = "simple_vlc_playback"
KEY_VLC_SUBTITLES_ON = "vlc_subtitles_on"
KEY_VLC_RESUME_PLAYBACK = "vlc_resume_playback"
KEY_VLC_TV_PLAYLIST = "vlc_tv_playlist"
KEY_VLC_PLAYLIST_ADVANCE = "vlc_playlist_advance"
KEY_BROWSE_ROW_RANDOM = "browse_row_random"
KEY_MEDIA_ROOTS = "media_roots"

_DEFAULTS: dict[str, bool] = {
    KEY_METADATA_ENABLED: METADATA_ENABLED,
    KEY_SCAN_ON_STARTUP: SCAN_ON_STARTUP,
    KEY_AUTO_GENERATE_THUMBNAILS: True,
    KEY_SIMPLE_VLC_PLAYBACK: False,
    KEY_VLC_SUBTITLES_ON: False,
    KEY_VLC_RESUME_PLAYBACK: True,
    KEY_VLC_TV_PLAYLIST: True,
    KEY_VLC_PLAYLIST_ADVANCE: True,
    KEY_BROWSE_ROW_RANDOM: False,
}

_cache: dict[str, bool] = {}
_media_roots_cache: list[dict] | None = None


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _parse_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


def _normalize_media_roots(roots: list) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    normalized: list[dict] = []
    for entry in roots:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path", "")).strip()
        root_type = entry.get("type", "")
        if not path or root_type not in ("movies", "tv"):
            continue
        key = (path.lower(), root_type)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"path": path, "type": root_type})
    return normalized


def init_settings(session: Session) -> None:
    global _media_roots_cache
    _cache.clear()
    _media_roots_cache = None
    for key, default in _DEFAULTS.items():
        row = session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=_bool_str(default))
            session.add(row)
            session.commit()
        _cache[key] = _parse_bool(row.value)

    row = session.get(AppSetting, KEY_MEDIA_ROOTS)
    if row is None:
        initial_roots = _normalize_media_roots(MEDIA_ROOTS)
        row = AppSetting(key=KEY_MEDIA_ROOTS, value=json.dumps(initial_roots))
        session.add(row)
        session.commit()
        _media_roots_cache = initial_roots
    else:
        try:
            parsed = json.loads(row.value)
            _media_roots_cache = _normalize_media_roots(parsed if isinstance(parsed, list) else [])
        except json.JSONDecodeError:
            _media_roots_cache = []


def get_bool(session: Session, key: str) -> bool:
    if key in _cache:
        return _cache[key]
    row = session.get(AppSetting, key)
    if row is None:
        return _DEFAULTS.get(key, False)
    value = _parse_bool(row.value)
    _cache[key] = value
    return value


def set_bool(session: Session, key: str, value: bool) -> None:
    row = session.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=_bool_str(value))
    else:
        row.value = _bool_str(value)
    session.add(row)
    session.commit()
    _cache[key] = value


def metadata_enabled() -> bool:
    return _cache.get(KEY_METADATA_ENABLED, METADATA_ENABLED)


def scan_on_startup() -> bool:
    return _cache.get(KEY_SCAN_ON_STARTUP, SCAN_ON_STARTUP)


def auto_generate_thumbnails() -> bool:
    return _cache.get(KEY_AUTO_GENERATE_THUMBNAILS, True)


def simple_vlc_playback() -> bool:
    return _cache.get(KEY_SIMPLE_VLC_PLAYBACK, False)


def vlc_subtitles_on() -> bool:
    if simple_vlc_playback():
        return False
    return _cache.get(KEY_VLC_SUBTITLES_ON, False)


def vlc_resume_playback() -> bool:
    if simple_vlc_playback():
        return False
    return _cache.get(KEY_VLC_RESUME_PLAYBACK, True)


def vlc_tv_playlist() -> bool:
    if simple_vlc_playback():
        return False
    return _cache.get(KEY_VLC_TV_PLAYLIST, True)


def vlc_playlist_advance() -> bool:
    if simple_vlc_playback():
        return False
    return _cache.get(KEY_VLC_PLAYLIST_ADVANCE, True)


def browse_row_random() -> bool:
    return _cache.get(KEY_BROWSE_ROW_RANDOM, False)


def media_roots() -> list[dict]:
    if _media_roots_cache is not None:
        return list(_media_roots_cache)
    return _normalize_media_roots(MEDIA_ROOTS)


def set_media_roots(session: Session, roots: list[dict]) -> None:
    global _media_roots_cache
    normalized = _normalize_media_roots(roots)
    row = session.get(AppSetting, KEY_MEDIA_ROOTS)
    payload = json.dumps(normalized)
    if row is None:
        row = AppSetting(key=KEY_MEDIA_ROOTS, value=payload)
    else:
        row.value = payload
    session.add(row)
    session.commit()
    _media_roots_cache = normalized


def _library_counts(session: Session) -> dict:
    movies = session.exec(select(func.count()).select_from(Movie)).one()
    shows = session.exec(select(func.count()).select_from(Show)).one()
    episodes = session.exec(select(func.count()).select_from(Episode)).one()
    return {"movies": movies, "shows": shows, "episodes": episodes}


def get_diagnostics(session: Session) -> dict:
    vlc_path = find_vlc_path()
    return {
        "vlc_path": vlc_path,
        "vlc_found": vlc_path is not None,
        "vlc_download_url": DEPENDENCIES["vlc"]["download_url"],
        "ffmpeg_available": ffmpeg_available(),
        "ffmpeg_download_url": DEPENDENCIES["ffmpeg"]["download_url"],
        "winget_available": winget_available(),
        "library_counts": _library_counts(session),
    }


def get_settings_payload(session: Session | None = None) -> dict:
    payload = {
        "metadata_enabled": metadata_enabled(),
        "scan_on_startup": scan_on_startup(),
        "auto_generate_thumbnails": auto_generate_thumbnails(),
        "simple_vlc_playback": simple_vlc_playback(),
        "vlc_subtitles_on": _cache.get(KEY_VLC_SUBTITLES_ON, False),
        "vlc_resume_playback": _cache.get(KEY_VLC_RESUME_PLAYBACK, True),
        "vlc_tv_playlist": _cache.get(KEY_VLC_TV_PLAYLIST, True),
        "vlc_playlist_advance": _cache.get(KEY_VLC_PLAYLIST_ADVANCE, True),
        "browse_row_random": _cache.get(KEY_BROWSE_ROW_RANDOM, False),
        "version": APP_VERSION,
        "github_url": GITHUB_URL,
    }
    if session is not None:
        payload["diagnostics"] = get_diagnostics(session)
    return payload
