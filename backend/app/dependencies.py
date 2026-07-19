"""Detect and install VLC / ffmpeg on Windows via winget."""

import shutil
import subprocess
import sys

from app.thumbnails import ffmpeg_available
from app.vlc import find_vlc_path

DEPENDENCIES: dict[str, dict[str, str]] = {
    "vlc": {
        "label": "VLC media player",
        "description": "Required for playback",
        "winget_id": "VideoLAN.VLC",
        "download_url": "https://www.videolan.org/vlc/",
    },
    "ffmpeg": {
        "label": "ffmpeg",
        "description": "Required for thumbnail generation",
        "winget_id": "Gyan.FFmpeg",
        "download_url": "https://ffmpeg.org/download.html",
    },
}


def winget_available() -> bool:
    return shutil.which("winget") is not None


def dependency_installed(name: str) -> bool:
    if name == "vlc":
        return find_vlc_path() is not None
    if name == "ffmpeg":
        return ffmpeg_available()
    raise ValueError(f"Unknown dependency: {name}")


def install_dependency(name: str) -> dict:
    if name not in DEPENDENCIES:
        raise ValueError(f"Unknown dependency: {name}")

    if dependency_installed(name):
        return {
            "started": False,
            "already_installed": True,
            "message": f"{DEPENDENCIES[name]['label']} is already installed.",
        }

    if not winget_available():
        return {
            "started": False,
            "message": (
                "winget is not available. Install manually from the project README "
                "or install the App Installer from the Microsoft Store."
            ),
        }

    winget_id = DEPENDENCIES[name]["winget_id"]
    cmd = [
        "winget",
        "install",
        "--id",
        winget_id,
        "-e",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    subprocess.Popen(cmd, creationflags=creationflags)

    return {
        "started": True,
        "message": (
            f"Installing {DEPENDENCIES[name]['label']}. Complete any prompts in the "
            "installer window, then refresh status below."
        ),
    }
