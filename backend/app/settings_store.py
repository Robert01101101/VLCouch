from sqlmodel import Session

from app.config import METADATA_ENABLED, SCAN_ON_STARTUP
from app.models import AppSetting

APP_VERSION = "0.1.0"
GITHUB_URL = "https://github.com/Robert01101101/VLCouch"

KEY_METADATA_ENABLED = "metadata_enabled"
KEY_SCAN_ON_STARTUP = "scan_on_startup"
KEY_AUTO_GENERATE_THUMBNAILS = "auto_generate_thumbnails"

_DEFAULTS: dict[str, bool] = {
    KEY_METADATA_ENABLED: METADATA_ENABLED,
    KEY_SCAN_ON_STARTUP: SCAN_ON_STARTUP,
    KEY_AUTO_GENERATE_THUMBNAILS: True,
}

_cache: dict[str, bool] = {}


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _parse_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


def init_settings(session: Session) -> None:
    _cache.clear()
    for key, default in _DEFAULTS.items():
        row = session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=_bool_str(default))
            session.add(row)
            session.commit()
        _cache[key] = _parse_bool(row.value)


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


def get_settings_payload() -> dict:
    return {
        "metadata_enabled": metadata_enabled(),
        "scan_on_startup": scan_on_startup(),
        "auto_generate_thumbnails": auto_generate_thumbnails(),
        "version": APP_VERSION,
        "github_url": GITHUB_URL,
    }
