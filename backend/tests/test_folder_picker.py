import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.folder_picker import (
    _PICKER_SCRIPT,
    PickFolderResult,
    open_folder,
    pick_folder,
    picker_available,
)


def _load_picker_module():
    """Import pick_folder_dialog.py as a module without running it as __main__.

    Importing (rather than just reading source) exercises the real Win32
    ctypes struct definitions and field assignments, which is where past
    regressions (e.g. LPWSTR marshaling on Python 3.12) actually broke.
    """
    spec = importlib.util.spec_from_file_location("pick_folder_dialog", _PICKER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_pick_folder_path_assigns_display_name_without_raising(monkeypatch):
    """Regression test for a ctypes TypeError on Python 3.12.

    Mocks only the native call that pops the UI (SHBrowseForFolderW);
    everything before it, including the BROWSEINFOW field assignment that
    previously raised `TypeError: incompatible types, c_wchar_Array_260
    instance instead of c_wchar_p instance`, runs for real.
    """
    module = _load_picker_module()
    monkeypatch.setattr(module.shell32, "SHBrowseForFolderW", lambda *_a: 0)

    assert module._pick_folder_path() is None


def test_main_initializes_com_as_apartment_threaded(monkeypatch):
    """SHBrowseForFolderW with BIF_NEWDIALOGSTYLE requires an STA. MTA makes
    it silently return NULL (no dialog, no error) instead of raising, which
    is indistinguishable from the user cancelling.
    """
    module = _load_picker_module()
    calls = []
    monkeypatch.setattr(
        module.ole32, "CoInitializeEx", lambda *args: calls.append(args)
    )
    monkeypatch.setattr(module.ole32, "CoUninitialize", lambda: None)
    monkeypatch.setattr(module, "_pick_folder_path", lambda: None)

    module.main()

    assert calls == [(None, module.COINIT_APARTMENTTHREADED)]
    assert module.COINIT_APARTMENTTHREADED == 0x2


@patch("app.folder_picker.os.startfile")
def test_open_folder_uses_startfile(mock_startfile):
    folder = Path("D:\\TV\\Breaking Bad")

    with patch("app.folder_picker.sys.platform", "win32"):
        open_folder(folder)

    mock_startfile.assert_called_once_with(folder)
