import logging
import subprocess
import winreg
from pathlib import Path

from sqlmodel import Session

from app.config import TEST_MODE, VLC_PATH
from app.models import Episode, Movie

logger = logging.getLogger(__name__)

DEFAULT_VLC_PATHS = [
    Path(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"),
]


def find_vlc_path() -> str | None:
    """Locate vlc.exe on Windows."""
    if VLC_PATH and Path(VLC_PATH).exists():
        return VLC_PATH

    # Check Windows registry
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC")
        install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
        winreg.CloseKey(key)
        vlc = Path(install_dir) / "vlc.exe"
        if vlc.exists():
            return str(vlc)
    except OSError:
        pass

    for path in DEFAULT_VLC_PATHS:
        if path.exists():
            return str(path)

    return None


def launch_vlc(file_path: str, subtitle_path: str | None = None) -> None:
    """Launch VLC to play a media file."""
    if TEST_MODE:
        logger.info("TEST_MODE: skipping VLC launch for %s", file_path)
        return

    vlc = find_vlc_path()
    if not vlc:
        raise FileNotFoundError(
            "VLC not found. Install VLC or set VLC_PATH in .env"
        )

    if not Path(file_path).exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    cmd = [vlc, file_path]
    if subtitle_path and Path(subtitle_path).exists():
        cmd.append(f"--sub-file={subtitle_path}")

    # DETACHED_PROCESS on Windows so VLC runs independently
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        cmd,
        creationflags=creationflags,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("Launched VLC: %s", file_path)


def play_item(session: Session, item_type: str, item_id: int) -> dict:
    """Resolve and play a movie or episode."""
    if item_type == "movie":
        item = session.get(Movie, item_id)
        if not item:
            raise ValueError(f"Movie {item_id} not found")
        launch_vlc(item.file_path, item.subtitle_path)
        return {"item_type": "movie", "item_id": item_id, "title": item.title}

    elif item_type == "episode":
        item = session.get(Episode, item_id)
        if not item:
            raise ValueError(f"Episode {item_id} not found")
        launch_vlc(item.file_path, item.subtitle_path)
        return {
            "item_type": "episode",
            "item_id": item_id,
            "title": f"S{item.season:02d}E{item.episode:02d}",
        }

    raise ValueError(f"Unknown item type: {item_type}")
