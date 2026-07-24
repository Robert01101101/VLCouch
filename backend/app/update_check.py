"""Check GitHub Releases for newer VLCouch versions."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

import httpx

from app.config import IS_TEST, TEST_MODE
from app.settings_store import APP_VERSION, GITHUB_URL

logger = logging.getLogger(__name__)

RELEASES_API = "https://api.github.com/repos/Robert01101101/VLCouch/releases/latest"
CACHE_TTL_SECONDS = 6 * 60 * 60
INSTALLER_ASSET_PATTERN = re.compile(r"^VLCouchSetup-.+\.exe$", re.IGNORECASE)

_cache: dict[str, Any] | None = None
_cache_at: float = 0.0
_check_lock = asyncio.Lock()


def _skip_update_check() -> bool:
    if IS_TEST or TEST_MODE:
        return True
    if os.getenv("VLCOUCH_SKIP_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        return True
    if os.getenv("APP_ENV", "production") == "dev":
        return True
    return False


def _parse_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV")
    parts: list[int] = []
    for segment in cleaned.split("."):
        digits = ""
        for ch in segment:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _version_gt(left: str, right: str) -> bool:
    return _parse_version(left) > _parse_version(right)


def _normalize_tag(tag_name: str) -> str:
    return tag_name.strip().lstrip("vV")


def _pick_installer_asset(assets: list[dict[str, Any]]) -> str | None:
    for asset in assets:
        name = asset.get("name") or ""
        if INSTALLER_ASSET_PATTERN.match(name):
            return asset.get("browser_download_url")
    return None


async def _fetch_latest_release() -> dict[str, Any] | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"VLCouch/{APP_VERSION}",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(RELEASES_API, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
    except Exception:
        logger.debug("Update check failed", exc_info=True)
        return None


def _build_status(
    release: dict[str, Any] | None,
    *,
    checked: bool,
    error: str | None = None,
) -> dict[str, Any]:
    current = APP_VERSION
    if release is None:
        return {
            "checked": checked,
            "update_available": False,
            "current_version": current,
            "latest_version": None,
            "download_url": None,
            "release_url": GITHUB_URL + "/releases",
            "error": error,
        }

    latest = _normalize_tag(release.get("tag_name", ""))
    download_url = _pick_installer_asset(release.get("assets") or [])
    release_url = release.get("html_url") or (GITHUB_URL + "/releases")
    update_available = bool(latest) and _version_gt(latest, current)

    return {
        "checked": checked,
        "update_available": update_available,
        "current_version": current,
        "latest_version": latest or None,
        "download_url": download_url,
        "release_url": release_url,
        "error": error,
    }


async def check_for_update(*, force: bool = False) -> dict[str, Any]:
    global _cache, _cache_at

    if _skip_update_check():
        return _build_status(None, checked=False)

    now = time.monotonic()
    if not force and _cache is not None and (now - _cache_at) < CACHE_TTL_SECONDS:
        return _cache

    async with _check_lock:
        now = time.monotonic()
        if not force and _cache is not None and (now - _cache_at) < CACHE_TTL_SECONDS:
            return _cache

        release = await _fetch_latest_release()
        status = _build_status(release, checked=True)
        _cache = status
        _cache_at = time.monotonic()
        return status


async def schedule_startup_check() -> None:
    if _skip_update_check():
        return
    await check_for_update()
