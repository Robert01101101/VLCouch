import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import TEST_MODE

logger = logging.getLogger(__name__)

_PICKER_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "pick_folder_dialog.py"


@dataclass(frozen=True)
class PickFolderResult:
    path: str | None = None
    available: bool = True
    cancelled: bool = False
    error: str | None = None


def picker_available() -> bool:
    """Return True when the native folder picker can be launched."""
    if TEST_MODE or sys.platform != "win32":
        return False
    return _PICKER_SCRIPT.exists()


def pick_folder() -> PickFolderResult:
    """Open a native folder picker on Windows."""
    if TEST_MODE:
        return PickFolderResult(
            available=False,
            error="Folder picker is not available in test mode",
        )
    if sys.platform != "win32":
        return PickFolderResult(
            available=False,
            error="Folder picker is only available on Windows",
        )
    if not _PICKER_SCRIPT.exists():
        logger.warning("Folder picker script not found: %s", _PICKER_SCRIPT)
        return PickFolderResult(
            available=False,
            error="Folder picker is not installed",
        )

    try:
        result = subprocess.run(
            [sys.executable, str(_PICKER_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Folder picker failed: %s", exc)
        return PickFolderResult(
            available=False,
            error="Folder picker failed to open",
        )

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        logger.warning("Folder picker failed: %s", detail)
        return PickFolderResult(
            available=False,
            error="Folder picker failed to open",
        )

    path = result.stdout.strip()
    if not path:
        return PickFolderResult(cancelled=True)
    return PickFolderResult(path=path)


def open_folder(path: Path) -> None:
    """Open a folder in File Explorer on Windows."""
    if sys.platform != "win32":
        raise OSError("Opening folders is only supported on Windows")
    os.startfile(path)  # noqa: S606
