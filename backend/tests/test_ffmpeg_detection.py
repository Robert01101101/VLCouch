import os
from pathlib import Path
from unittest.mock import patch

from app.thumbnails import find_ffmpeg_path


@patch("app.thumbnails.FFMPEG_PATH", r"C:\custom\ffmpeg.exe")
@patch("app.thumbnails.Path.exists", return_value=True)
def test_find_ffmpeg_path_uses_env_override(mock_exists):
    assert find_ffmpeg_path() == r"C:\custom\ffmpeg.exe"
    mock_exists.assert_called()


@patch("app.thumbnails.FFMPEG_PATH", "")
@patch("app.thumbnails.shutil.which", return_value="/usr/bin/ffmpeg")
def test_find_ffmpeg_path_uses_path(mock_which):
    assert find_ffmpeg_path() == "/usr/bin/ffmpeg"
    mock_which.assert_called_once_with("ffmpeg")


@patch("app.thumbnails.FFMPEG_PATH", "")
@patch("app.thumbnails.shutil.which", return_value=None)
@patch("app.thumbnails.sys.platform", "win32")
def test_find_ffmpeg_path_uses_winget_links(mock_which, tmp_path, monkeypatch):
    links = tmp_path / "WinGet" / "Links"
    links.mkdir(parents=True)
    ffmpeg = links / "ffmpeg.exe"
    ffmpeg.write_text("", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    with patch("app.thumbnails._winget_link_dirs", return_value=[links]):
        assert find_ffmpeg_path() == str(ffmpeg)


@patch("app.thumbnails.FFMPEG_PATH", "")
@patch("app.thumbnails.shutil.which", return_value=None)
@patch("app.thumbnails.sys.platform", "win32")
def test_find_ffmpeg_path_uses_winget_package_dir(mock_which, tmp_path, monkeypatch):
    package_root = (
        tmp_path
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "ffmpeg-8.1.2-full_build"
        / "bin"
    )
    package_root.mkdir(parents=True)
    ffmpeg = package_root / "ffmpeg.exe"
    ffmpeg.write_text("", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert find_ffmpeg_path() == str(ffmpeg)


@patch("app.thumbnails.FFMPEG_PATH", "")
@patch("app.thumbnails.shutil.which", return_value=None)
@patch("app.thumbnails.sys.platform", "win32")
def test_find_ffmpeg_path_prefers_newest_winget_package(mock_which, tmp_path, monkeypatch):
    packages = tmp_path / "Microsoft" / "WinGet" / "Packages"
    old_bin = (
        packages
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "ffmpeg-7.0-full_build"
        / "bin"
    )
    new_bin = (
        packages
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "ffmpeg-8.1.2-full_build"
        / "bin"
    )
    old_bin.mkdir(parents=True)
    new_bin.mkdir(parents=True)
    old_ffmpeg = old_bin / "ffmpeg.exe"
    new_ffmpeg = new_bin / "ffmpeg.exe"
    old_ffmpeg.write_text("", encoding="utf-8")
    new_ffmpeg.write_text("", encoding="utf-8")
    os.utime(old_ffmpeg, (1, 1))
    os.utime(new_ffmpeg, (2, 2))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert find_ffmpeg_path() == str(new_ffmpeg)


@patch("app.thumbnails.FFMPEG_PATH", "")
@patch("app.thumbnails.shutil.which", return_value=None)
@patch("app.thumbnails.sys.platform", "linux")
def test_find_ffmpeg_path_returns_none_when_missing(mock_which):
    assert find_ffmpeg_path() is None
