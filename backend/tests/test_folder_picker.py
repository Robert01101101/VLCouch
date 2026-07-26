import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.folder_picker import (
    PickFolderResult,
    _PICKER_SCRIPT,
    open_folder,
    pick_folder,
    picker_available,
)


def test_pick_folder_uses_subprocess_script():
    assert _PICKER_SCRIPT.name == "pick_folder_dialog.py"
    assert _PICKER_SCRIPT.exists()


def test_pick_folder_returns_unavailable_in_test_mode():
    result = pick_folder()
    assert result == PickFolderResult(
        available=False,
        error="Folder picker is not available in test mode",
    )


def test_picker_available_false_in_test_mode():
    assert picker_available() is False


@patch("app.folder_picker.subprocess.run")
def test_pick_folder_returns_selected_path(mock_run):
    mock_run.return_value = MagicMock(stdout="D:\\Movies\n", stderr="", returncode=0)

    with patch("app.folder_picker.TEST_MODE", False), patch(
        "app.folder_picker.sys.platform", "win32"
    ):
        result = pick_folder()

    assert result == PickFolderResult(path="D:\\Movies")
    assert mock_run.call_args[0][0] == [sys.executable, str(_PICKER_SCRIPT)]


@patch("app.folder_picker.subprocess.run")
def test_pick_folder_returns_cancelled_when_empty(mock_run):
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

    with patch("app.folder_picker.TEST_MODE", False), patch(
        "app.folder_picker.sys.platform", "win32"
    ):
        result = pick_folder()

    assert result == PickFolderResult(cancelled=True)


@patch("app.folder_picker._PICKER_SCRIPT")
def test_pick_folder_returns_unavailable_when_script_missing(mock_script):
    mock_script.exists.return_value = False

    with patch("app.folder_picker.TEST_MODE", False), patch(
        "app.folder_picker.sys.platform", "win32"
    ):
        result = pick_folder()

    assert result.available is False
    assert result.error == "Folder picker is not installed"


@patch("app.folder_picker.subprocess.run")
def test_pick_folder_returns_unavailable_on_subprocess_error(mock_run):
    mock_run.side_effect = OSError("boom")

    with patch("app.folder_picker.TEST_MODE", False), patch(
        "app.folder_picker.sys.platform", "win32"
    ):
        result = pick_folder()

    assert result.available is False
    assert result.error == "Folder picker failed to open"


def test_pick_folder_dialog_script_has_no_tkinter_import():
    source = _PICKER_SCRIPT.read_text(encoding="utf-8")
    assert "import tkinter" not in source
    assert "from tkinter" not in source


@patch("app.folder_picker.os.startfile")
def test_open_folder_uses_startfile(mock_startfile):
    folder = Path("D:\\TV\\Breaking Bad")

    with patch("app.folder_picker.sys.platform", "win32"):
        open_folder(folder)

    mock_startfile.assert_called_once_with(folder)
