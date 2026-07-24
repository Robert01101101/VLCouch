import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app import update_check


@pytest.fixture(autouse=True)
def reset_update_cache():
    update_check._cache = None
    update_check._cache_at = 0.0
    yield
    update_check._cache = None
    update_check._cache_at = 0.0


def test_parse_version_comparison():
    assert update_check._version_gt("0.2.0", "0.1.0")
    assert update_check._version_gt("1.0.0", "0.9.9")
    assert not update_check._version_gt("0.1.0", "0.1.0")
    assert not update_check._version_gt("0.1.0", "0.2.0")


def test_normalize_tag():
    assert update_check._normalize_tag("v0.2.0") == "0.2.0"


def test_pick_installer_asset():
    assets = [
        {"name": "notes.txt", "browser_download_url": "https://example.com/notes.txt"},
        {
            "name": "VLCouchSetup-0.2.0.exe",
            "browser_download_url": "https://example.com/VLCouchSetup-0.2.0.exe",
        },
    ]
    assert update_check._pick_installer_asset(assets) == "https://example.com/VLCouchSetup-0.2.0.exe"


def test_check_for_update_skips_in_test_mode(monkeypatch):
    monkeypatch.setattr(update_check, "IS_TEST", True)
    status = asyncio.run(update_check.check_for_update(force=True))
    assert status["checked"] is False
    assert status["update_available"] is False


def test_check_for_update_reports_newer_release(monkeypatch):
    monkeypatch.setattr(update_check, "IS_TEST", False)
    monkeypatch.setattr(update_check, "TEST_MODE", False)
    monkeypatch.setattr(update_check, "APP_VERSION", "0.1.0")

    release = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/Robert01101101/VLCouch/releases/tag/v0.2.0",
        "assets": [
            {
                "name": "VLCouchSetup-0.2.0.exe",
                "browser_download_url": "https://example.com/VLCouchSetup-0.2.0.exe",
            }
        ],
    }

    with patch(
        "app.update_check._fetch_latest_release",
        new=AsyncMock(return_value=release),
    ):
        status = asyncio.run(update_check.check_for_update(force=True))

    assert status["checked"] is True
    assert status["update_available"] is True
    assert status["latest_version"] == "0.2.0"
    assert status["download_url"] == "https://example.com/VLCouchSetup-0.2.0.exe"


def test_check_for_update_uses_cache(monkeypatch):
    monkeypatch.setattr(update_check, "IS_TEST", False)
    monkeypatch.setattr(update_check, "TEST_MODE", False)
    monkeypatch.setattr(update_check, "APP_VERSION", "0.1.0")

    release = {
        "tag_name": "v0.1.0",
        "html_url": "https://github.com/Robert01101101/VLCouch/releases/latest",
        "assets": [],
    }
    mock_fetch = AsyncMock(return_value=release)

    with patch("app.update_check._fetch_latest_release", new=mock_fetch):
        asyncio.run(update_check.check_for_update(force=True))
        asyncio.run(update_check.check_for_update(force=False))

    assert mock_fetch.await_count == 1
