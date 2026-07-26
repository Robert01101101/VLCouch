"""Standalone folder picker subprocess (Windows).

Opened separately from the API server so the dialog can be forced to the
foreground above the browser. Uses SHBrowseForFolderW (no tkinter).
"""

from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32

BIF_RETURNONLYFSDIRS = 0x0001
BIF_NEWDIALOGSTYLE = 0x0040

DIALOG_TITLE_FRAGMENTS = (
    "browse for folder",
    "select folder",
    "select a folder",
    "choose folder",
)


class BROWSEINFOW(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR),
        ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", ctypes.c_longlong),
        ("iImage", ctypes.c_int),
    ]


def _window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _should_focus(hwnd: int) -> bool:
    if not user32.IsWindowVisible(hwnd):
        return False

    title = _window_text(hwnd).lower()
    if title and any(fragment in title for fragment in DIALOG_TITLE_FRAGMENTS):
        return True

    return _class_name(hwnd) == "#32770" and bool(title)


def _force_foreground(hwnd: int) -> None:
    foreground = user32.GetForegroundWindow()
    if foreground == hwnd:
        return

    current_thread = kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    attached = False
    if foreground_thread and foreground_thread != current_thread:
        attached = bool(
            user32.AttachThreadInput(foreground_thread, current_thread, True)
        )

    try:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003 | 0x0040)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0003 | 0x0040)
    finally:
        if attached:
            user32.AttachThreadInput(foreground_thread, current_thread, False)


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _bring_picker_to_front(stop: threading.Event) -> None:
    def callback(hwnd, _lparam):
        if stop.is_set():
            return False
        if _should_focus(hwnd):
            _force_foreground(hwnd)
        return True

    enum_proc = WNDENUMPROC(callback)
    while not stop.is_set():
        user32.EnumWindows(enum_proc, 0)
        stop.wait(0.05)


def _pick_folder_path() -> str | None:
    display_name = ctypes.create_unicode_buffer(260)
    bi = BROWSEINFOW()
    bi.lpszTitle = "Select a folder"
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE
    bi.pszDisplayName = display_name

    pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
    if not pidl:
        return None

    path_buf = ctypes.create_unicode_buffer(260)
    try:
        if not shell32.SHGetPathFromIDListW(pidl, path_buf):
            return None
        return path_buf.value
    finally:
        ole32.CoTaskMemFree(pidl)


def main() -> int:
    ole32.CoInitializeEx(None, 0)
    stop = threading.Event()
    worker = threading.Thread(target=_bring_picker_to_front, args=(stop,), daemon=True)
    worker.start()

    try:
        path = _pick_folder_path()
    finally:
        stop.set()
        ole32.CoUninitialize()

    if path:
        print(path, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
