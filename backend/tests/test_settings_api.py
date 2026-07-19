from unittest.mock import MagicMock, patch

import app.settings_store as settings_store
from app.metadata import enrich_show, lookup_overview
from app.models import Show


def test_get_settings_returns_defaults(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata_enabled"] is False
    assert data["scan_on_startup"] is False
    assert data["auto_generate_thumbnails"] is True
    assert data["simple_vlc_playback"] is False
    assert data["vlc_subtitles_on"] is False
    assert data["vlc_resume_playback"] is True
    assert data["vlc_tv_playlist"] is True
    assert data["vlc_playlist_advance"] is True
    assert data["browse_row_random"] is False
    assert data["version"] == settings_store.APP_VERSION
    assert data["github_url"] == settings_store.GITHUB_URL
    assert "diagnostics" in data
    assert "vlc_path" in data["diagnostics"]
    assert "vlc_found" in data["diagnostics"]
    assert "ffmpeg_available" in data["diagnostics"]
    assert "winget_available" in data["diagnostics"]
    assert "vlc_download_url" in data["diagnostics"]
    assert "ffmpeg_download_url" in data["diagnostics"]
    counts = data["diagnostics"]["library_counts"]
    assert set(counts.keys()) == {"movies", "shows", "episodes"}
    assert all(isinstance(counts[key], int) for key in counts)


def test_patch_settings_persists(client):
    response = client.patch(
        "/api/settings",
        json={
            "metadata_enabled": True,
            "scan_on_startup": True,
            "auto_generate_thumbnails": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata_enabled"] is True
    assert data["scan_on_startup"] is True
    assert data["auto_generate_thumbnails"] is True

    response = client.get("/api/settings")
    assert response.json()["metadata_enabled"] is True
    assert response.json()["scan_on_startup"] is True
    assert response.json()["auto_generate_thumbnails"] is True


def test_lookup_overview_makes_no_http_when_disabled(client):
    client.patch("/api/settings", json={"metadata_enabled": False})

    with patch("app.metadata.httpx.Client") as mock_client:
        result = lookup_overview("Breaking Bad", "tv")
        assert result is None
        mock_client.assert_not_called()


def test_enrich_show_makes_no_http_when_disabled(client, tmp_path):
    from sqlmodel import Session

    from app.db import engine

    client.patch("/api/settings", json={"metadata_enabled": False})

    with Session(engine) as session:
        show = Show(title="Test Show", normalized_title="test-show-no-wiki")
        session.add(show)
        session.commit()
        session.refresh(show)

        with patch("app.metadata.httpx.Client") as mock_client:
            enrich_show(session, show)
            mock_client.assert_not_called()

        session.refresh(show)
        assert show.overview is None


def test_enrich_show_fetches_when_enabled(client):
    from sqlmodel import Session

    from app.db import engine

    client.patch("/api/settings", json={"metadata_enabled": True})

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = ["Breaking Bad (TV series)", ["Breaking Bad (TV series)"], [], []]
    mock_summary = MagicMock()
    mock_summary.status_code = 200
    mock_summary.raise_for_status = MagicMock()
    mock_summary.json.return_value = {"extract": "A chemistry teacher turns to crime."}

    with Session(engine) as session:
        show = Show(title="Breaking Bad", normalized_title="breaking-bad-wiki-test")
        session.add(show)
        session.commit()
        session.refresh(show)

        with patch("app.metadata.httpx.Client") as mock_client:
            instance = mock_client.return_value.__enter__.return_value
            instance.get.side_effect = [mock_response, mock_summary]
            enrich_show(session, show)
            assert instance.get.call_count == 2

        session.refresh(show)
        assert show.overview == "A chemistry teacher turns to crime."


def test_patch_vlc_subtitles_on_persists(client):
    response = client.patch("/api/settings", json={"vlc_subtitles_on": True})
    assert response.status_code == 200
    assert response.json()["vlc_subtitles_on"] is True

    response = client.get("/api/settings")
    assert response.json()["vlc_subtitles_on"] is True


def test_enabling_auto_thumbnails_queues_backfill(client):
    client.patch("/api/settings", json={"auto_generate_thumbnails": False})

    with patch("app.routers.settings.queue_all_thumbnails_backfill") as mock_queue:
        response = client.patch(
            "/api/settings",
            json={"auto_generate_thumbnails": True},
        )
        assert response.status_code == 200
        assert response.json()["auto_generate_thumbnails"] is True
        mock_queue.assert_called_once()


def test_disabling_auto_thumbnails_does_not_queue_backfill(client):
    client.patch("/api/settings", json={"auto_generate_thumbnails": True})

    with patch("app.routers.settings.queue_all_thumbnails_backfill") as mock_queue:
        response = client.patch(
            "/api/settings",
            json={"auto_generate_thumbnails": False},
        )
        assert response.status_code == 200
        assert response.json()["auto_generate_thumbnails"] is False
        mock_queue.assert_not_called()


def test_install_dependency_unknown(client):
    response = client.post("/api/dependencies/notreal/install")
    assert response.status_code == 400


def test_install_dependency_unavailable_in_test_mode(client):
    response = client.post("/api/dependencies/vlc/install")
    assert response.status_code == 503


@patch("app.dependencies.subprocess.Popen")
@patch("app.dependencies.winget_available", return_value=True)
@patch("app.dependencies.dependency_installed", return_value=False)
def test_install_dependency_starts_winget(mock_installed, mock_winget, mock_popen):
    from app.dependencies import install_dependency

    result = install_dependency("vlc")

    assert result["started"] is True
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args.args[0]
    assert "VideoLAN.VLC" in cmd


@patch("app.dependencies.dependency_installed", return_value=True)
def test_install_dependency_already_installed(mock_installed):
    from app.dependencies import install_dependency

    result = install_dependency("ffmpeg")

    assert result["started"] is False
    assert result["already_installed"] is True
