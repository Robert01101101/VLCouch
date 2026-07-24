import logging
import os
import subprocess
import uuid
import winreg
from pathlib import Path

from sqlmodel import Session

from app import settings_store
from app.config import PLAYLISTS_DIR, TEST_MODE, VLC_PATH
from app.library_progress import remaining_unwatched_episodes
from app.models import Episode
from app.playback_poller import start_poller
from app.playback_service import (
    create_session,
    generate_http_password,
    resolve_playable,
)
from app.vlc_http import allocate_http_port
from app.vlc_playlist import build_m3u
from app.watch_service import get_resume_position

logger = logging.getLogger(__name__)

# Bump when VLC launch args change; exposed on /api/health so stale servers are obvious.
VLC_LAUNCH_PROFILE = "2026-07-playlist-clicked-episode-fix"

DEFAULT_VLC_PATHS = [
    Path(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"),
]


def find_vlc_path() -> str | None:
    """Locate vlc.exe on Windows."""
    if VLC_PATH and Path(VLC_PATH).exists():
        return VLC_PATH

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


def _vlc_launch_env(install_dir: Path) -> dict[str, str]:
    """Ensure VLC can locate plugins when spawned from another working directory."""
    env = os.environ.copy()
    plugins_dir = install_dir / "plugins"
    if plugins_dir.is_dir():
        env["VLC_PLUGIN_PATH"] = str(plugins_dir)
    return env


def _subtitle_launch_args(subtitle_path: str | None) -> list[str]:
    """Build VLC subtitle CLI args from user settings and detected subtitle file."""
    if settings_store.simple_vlc_playback() or not settings_store.vlc_subtitles_on():
        return []
    cmd: list[str] = []
    if subtitle_path and Path(subtitle_path).exists():
        cmd.append(f"--sub-file={subtitle_path}")
    cmd.append("--sub-track=0")
    return cmd


def _playlist_behavior_args() -> list[str]:
    """Prevent VLC from looping the current item or entire playlist."""
    if settings_store.vlc_playlist_advance():
        return ["--no-repeat", "--no-loop"]
    return []


def _resolve_resume(
    session: Session,
    item_type: str,
    item_id: int,
    *,
    from_start: bool,
) -> float | None:
    if from_start or not settings_store.vlc_resume_playback():
        return None
    return get_resume_position(session, item_type, item_id)


def _http_launch_args(http_port: int, http_password: str) -> list[str]:
    return [
        "--intf=qt",
        "--no-one-instance",
        "--extraintf=http",
        "--http-host=127.0.0.1",
        f"--http-port={http_port}",
        f"--http-password={http_password}",
    ]


def _launch_vlc_process(cmd: list[str]) -> int | None:
    if TEST_MODE:
        logger.info("TEST_MODE: skipping VLC launch: %s", cmd)
        return None

    vlc = find_vlc_path()
    if not vlc:
        raise FileNotFoundError(
            "VLC not found. Install VLC or set VLC_PATH in .env"
        )

    vlc_path = Path(vlc)
    install_dir = vlc_path.parent
    launch_env = _vlc_launch_env(install_dir)
    full_cmd = [str(vlc_path), *cmd]
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        full_cmd,
        cwd=str(install_dir),
        env=launch_env,
        creationflags=creationflags,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("Launched VLC from %s (pid %s)", install_dir, proc.pid)
    return proc.pid


def launch_simple(
    *,
    item_type: str,
    item_id: int,
    file_path: str,
    subtitle_path: str | None,
    title: str,
) -> dict:
    """Launch VLC with minimal args (no HTTP tracking or binge playlists)."""
    if not TEST_MODE and not Path(file_path).exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    cmd = [file_path]
    _launch_vlc_process(cmd)

    return {
        "item_type": item_type,
        "item_id": item_id,
        "title": title,
        "mode": "simple",
        "session_id": None,
        "resumed_from_seconds": None,
        "playlist_count": 1,
        "watched": False,
    }


def launch_single(
    session: Session,
    *,
    item_type: str,
    item_id: int,
    file_path: str,
    subtitle_path: str | None,
    title: str,
    from_start: bool,
) -> dict:
    if not TEST_MODE and not Path(file_path).exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    resume = _resolve_resume(session, item_type, item_id, from_start=from_start)
    http_port = allocate_http_port()
    http_password = generate_http_password()

    cmd = _http_launch_args(http_port, http_password)
    if resume:
        cmd.append(f"--start-time={resume}")
    cmd.extend(_subtitle_launch_args(subtitle_path))
    cmd.append(file_path)

    pid = _launch_vlc_process(cmd)
    playback = create_session(
        session,
        mode="single",
        pid=pid,
        http_port=http_port,
        http_password=http_password,
        playlist_path=None,
        current_item_type=item_type,
        current_item_id=item_id,
    )
    start_poller()

    return {
        "item_type": item_type,
        "item_id": item_id,
        "title": title,
        "mode": "single",
        "session_id": playback.id,
        "resumed_from_seconds": resume,
        "playlist_count": 1,
        "watched": False,
    }


def launch_playlist(
    session: Session,
    *,
    episode: Episode,
    from_start: bool,
) -> dict:
    episodes = remaining_unwatched_episodes(session, episode.show_id, episode)
    if not episodes:
        raise ValueError(f"No unwatched episodes from episode {episode.id}")

    start_times: dict[int, float] = {}
    if not from_start and settings_store.vlc_resume_playback():
        resume = get_resume_position(session, "episode", episode.id)
        if resume:
            start_times[episode.id] = resume

    if not TEST_MODE:
        for ep in episodes:
            if not Path(ep.file_path).exists():
                raise FileNotFoundError(f"Media file not found: {ep.file_path}")

    session_id = str(uuid.uuid4())
    playlist_path = str(PLAYLISTS_DIR / f"{session_id}.m3u")
    Path(playlist_path).write_text(
        build_m3u(
            episodes,
            start_times=start_times,
            subtitles_on=settings_store.vlc_subtitles_on(),
        ),
        encoding="utf-8",
    )

    http_port = allocate_http_port()
    http_password = generate_http_password()
    cmd = [
        *_http_launch_args(http_port, http_password),
        "--playlist-autostart",
        *_playlist_behavior_args(),
    ]
    cmd.append(playlist_path)
    pid = _launch_vlc_process(cmd)

    playlist_items = [
        ("episode", ep.id, ep.file_path) for ep in episodes
    ]
    playback = create_session(
        session,
        mode="playlist",
        pid=pid,
        http_port=http_port,
        http_password=http_password,
        playlist_path=playlist_path,
        current_item_type="episode",
        current_item_id=episode.id,
        playlist_items=playlist_items,
        session_id=session_id,
    )
    start_poller()

    return {
        "item_type": "episode",
        "item_id": episode.id,
        "title": f"S{episode.season:02d}E{episode.episode:02d}",
        "mode": "playlist",
        "session_id": playback.id,
        "resumed_from_seconds": start_times.get(episode.id),
        "playlist_count": len(episodes),
        "watched": False,
    }


def play_item(
    session: Session,
    item_type: str,
    item_id: int,
    *,
    from_start: bool = False,
) -> dict:
    """Resolve and play a movie or episode with playback tracking."""
    if settings_store.simple_vlc_playback():
        if item_type == "movie":
            file_path, subtitle_path, title = resolve_playable(session, item_type, item_id)
            return launch_simple(
                item_type=item_type,
                item_id=item_id,
                file_path=file_path,
                subtitle_path=subtitle_path,
                title=title,
            )
        if item_type == "episode":
            file_path, subtitle_path, title = resolve_playable(session, item_type, item_id)
            return launch_simple(
                item_type=item_type,
                item_id=item_id,
                file_path=file_path,
                subtitle_path=subtitle_path,
                title=title,
            )
        raise ValueError(f"Unknown item type: {item_type}")

    if item_type == "movie":
        file_path, subtitle_path, title = resolve_playable(session, item_type, item_id)
        return launch_single(
            session,
            item_type=item_type,
            item_id=item_id,
            file_path=file_path,
            subtitle_path=subtitle_path,
            title=title,
            from_start=from_start,
        )

    if item_type == "episode":
        episode = session.get(Episode, item_id)
        if not episode:
            raise ValueError(f"Episode {item_id} not found")
        if settings_store.vlc_tv_playlist():
            return launch_playlist(session, episode=episode, from_start=from_start)
        file_path, subtitle_path, title = resolve_playable(session, item_type, item_id)
        return launch_single(
            session,
            item_type=item_type,
            item_id=item_id,
            file_path=file_path,
            subtitle_path=subtitle_path,
            title=title,
            from_start=from_start,
        )

    raise ValueError(f"Unknown item type: {item_type}")
