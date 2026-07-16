import logging
import subprocess
import sys

from app.config import TEST_MODE

logger = logging.getLogger(__name__)

_PICK_FOLDER_PS = """
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = 'Select a media folder'
$d.ShowNewFolderButton = $false
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $d.SelectedPath
}
"""


def pick_folder() -> str | None:
    """Open a native folder picker on Windows. Returns None if cancelled or unavailable."""
    if TEST_MODE or sys.platform != "win32":
        return None

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Sta", "-Command", _PICK_FOLDER_PS],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Folder picker failed: %s", exc)
        return None

    path = result.stdout.strip()
    return path if path else None
