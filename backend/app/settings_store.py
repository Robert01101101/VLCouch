import json

from sqlmodel import Session

from app.config import MEDIA_ROOTS, METADATA_ENABLED, SCAN_ON_STARTUP
from app.models import AppSetting

APP_VERSION = "0.1.0"
GITHUB_URL = "https://github.com/Robert01101101/VLCouch"

KEY_METADATA_ENABLED = "metadata_enabled"
KEY_SCAN_ON_STARTUP = "scan_on_startup"
KEY_AUTO_GENERATE_THUMBNAILS = "auto_generate_thumbnails"
KEY_MEDIA_ROOTS = "media_roots"

_DEFAULTS: dict[str, bool] = {
    KEY_METADATA_ENABLED: METADATA_ENABLED,
    KEY_SCAN_ON_STARTUP: SCAN_ON_STARTUP,
    KEY_AUTO_GENERATE_THUMBNAILS: True,
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


def get_settings_payload() -> dict:
    return {
        "metadata_enabled": metadata_enabled(),
        "scan_on_startup": scan_on_startup(),
        "auto_generate_thumbnails": auto_generate_thumbnails(),
        "version": APP_VERSION,
        "github_url": GITHUB_URL,
    }
