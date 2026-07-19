import logging
import os
import subprocess
import sys
from pathlib import Path

from app.config import TEST_MODE

logger = logging.getLogger(__name__)

_PICKER_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "pick_folder_dialog.py"


def pick_folder() -> str | None:
    """Open a native folder picker on Windows. Returns None if cancelled or unavailable."""
    if TEST_MODE or sys.platform != "win32":
        return None

    if not _PICKER_SCRIPT.exists():
        logger.warning("Folder picker script not found: %s", _PICKER_SCRIPT)
        return None

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
        return None

    if result.returncode != 0 and result.stderr.strip():
        logger.warning("Folder picker stderr: %s", result.stderr.strip())

    path = result.stdout.strip()
    return path if path else None


def open_folder(path: Path) -> None:
    """Open a folder in File Explorer on Windows."""
    if sys.platform != "win32":
        raise OSError("Opening folders is only supported on Windows")
    os.startfile(path)  # noqa: S606
