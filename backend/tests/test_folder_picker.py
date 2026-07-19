import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.folder_picker import _PICKER_SCRIPT, open_folder, pick_folder


def test_pick_folder_uses_subprocess_script():
    assert _PICKER_SCRIPT.name == "pick_folder_dialog.py"
    assert _PICKER_SCRIPT.exists()


def test_pick_folder_returns_none_in_test_mode():
    assert pick_folder() is None


@patch("app.folder_picker.subprocess.run")
def test_pick_folder_returns_selected_path(mock_run):
    mock_run.return_value = MagicMock(stdout="D:\\Movies\n", stderr="", returncode=0)

    with patch("app.folder_picker.TEST_MODE", False), patch(
        "app.folder_picker.sys.platform", "win32"
    ):
        assert pick_folder() == "D:\\Movies"

    assert mock_run.call_args[0][0] == [sys.executable, str(_PICKER_SCRIPT)]


@patch("app.folder_picker.os.startfile")
def test_open_folder_uses_startfile(mock_startfile):
    folder = Path("D:\\TV\\Breaking Bad")

    with patch("app.folder_picker.sys.platform", "win32"):
        open_folder(folder)

    mock_startfile.assert_called_once_with(folder)
