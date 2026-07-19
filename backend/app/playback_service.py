"""Playback session lifecycle and position persistence."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

import app.db as db
from app.config import PLAYLISTS_DIR, TEST_MODE
from app import settings_store
from app.models import Episode, Movie, PlaybackSession, PlaybackSessionItem
from app.vlc_http import (
    VlcStatus,
    fetch_playlist_map,
    fetch_status,
    is_pid_alive,
    is_playback_complete,
    terminate_pid,
)
from app.library_progress import progress_percent
from app.watch_service import mark_completed, touch_play_started, update_position

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.utcnow()


def _should_persist_position(status: VlcStatus) -> bool:
    """Ignore idle polls that would overwrite a saved resume point with zero."""
    if status.length > 0 or status.time > 0:
        return True
    return status.state in ("playing", "paused")


def get_active_session(session: Session) -> PlaybackSession | None:
    return session.exec(
        select(PlaybackSession).where(PlaybackSession.status == "active")
    ).first()


def sweep_stale_sessions() -> None:
    """Mark orphaned active sessions ended and remove old playlist files."""
    with Session(db.engine) as session:
        active = session.exec(
            select(PlaybackSession).where(PlaybackSession.status == "active")
        ).all()
        for playback in active:
            if playback.pid and not is_pid_alive(playback.pid):
                finalize_session(session, playback.id, save_position=True)
        session.commit()

    if PLAYLISTS_DIR.exists():
        cutoff = _now().timestamp() - 86400
        for path in PLAYLISTS_DIR.glob("*.m3u"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                pass


def finalize_active_session(session: Session, *, terminate_vlc: bool = True) -> None:
    active = get_active_session(session)
    if active:
        finalize_session(session, active.id, save_position=True, terminate_vlc=terminate_vlc)


def finalize_session(
    session: Session,
    session_id: str,
    *,
    save_position: bool = True,
    terminate_vlc: bool = False,
    status: str = "ended",
) -> None:
    playback = session.get(PlaybackSession, session_id)
    if not playback or playback.status != "active":
        return

    if save_position and settings_store.vlc_resume_playback() and playback.http_port and playback.http_password:
        status_data = fetch_status(playback.http_port, playback.http_password)
        if (
            status_data
            and playback.current_item_type
            and playback.current_item_id
            and _should_persist_position(status_data)
        ):
            update_position(
                session,
                playback.current_item_type,
                playback.current_item_id,
                status_data.time,
                status_data.length,
            )
            if is_playback_complete(status_data):
                mark_completed(session, playback.current_item_type, playback.current_item_id)

    if terminate_vlc and playback.pid:
        terminate_pid(playback.pid)

    playback.status = status
    playback.ended_at = _now()
    session.add(playback)
    session.commit()

    if playback.playlist_path:
        Path(playback.playlist_path).unlink(missing_ok=True)


def create_session(
    session: Session,
    *,
    mode: str,
    pid: int | None,
    http_port: int,
    http_password: str,
    playlist_path: str | None,
    current_item_type: str,
    current_item_id: int,
    playlist_items: list[tuple[str, int, str]] | None = None,
    session_id: str | None = None,
) -> PlaybackSession:
    finalize_active_session(session, terminate_vlc=True)

    playback_id = session_id or str(uuid.uuid4())
    playback = PlaybackSession(
        id=playback_id,
        status="active",
        mode=mode,
        pid=pid if not TEST_MODE else None,
        http_port=http_port,
        http_password=http_password,
        playlist_path=playlist_path,
        current_item_type=current_item_type,
        current_item_id=current_item_id,
        started_at=_now(),
    )
    session.add(playback)
    session.flush()

    if playlist_items:
        for sequence, (item_type, item_id, file_path) in enumerate(playlist_items):
            session.add(
                PlaybackSessionItem(
                    session_id=playback_id,
                    sequence=sequence,
                    item_type=item_type,
                    item_id=item_id,
                    file_path=file_path,
                )
            )

    touch_play_started(session, current_item_type, current_item_id)
    session.commit()
    session.refresh(playback)
    return playback


def generate_http_password() -> str:
    # Hex-only avoids values starting with "-" being parsed as CLI flags.
    return secrets.token_hex(16)


def resolve_item_from_plid(
    session: Session,
    playback: PlaybackSession,
    plid: int,
    playlist_map: dict[int, str],
) -> tuple[str, int] | None:
    items = session.exec(
        select(PlaybackSessionItem)
        .where(PlaybackSessionItem.session_id == playback.id)
        .order_by(PlaybackSessionItem.sequence)
    ).all()

    uri = playlist_map.get(plid)
    if uri:
        for item in items:
            if Path(item.file_path).name.lower() in uri.lower():
                return item.item_type, item.item_id

    for item in items:
        if item.plid == plid:
            return item.item_type, item.item_id
    return None


def poll_session(session: Session, session_id: str) -> bool:
    """Poll one session. Returns False when session should stop being tracked."""
    playback = session.get(PlaybackSession, session_id)
    if not playback or playback.status != "active":
        return False

    if playback.pid and not is_pid_alive(playback.pid):
        finalize_session(session, playback.id, save_position=True)
        return False

    if not playback.http_port or not playback.http_password:
        return True

    status_data = fetch_status(playback.http_port, playback.http_password)
    if status_data is None:
        if playback.pid and not is_pid_alive(playback.pid):
            finalize_session(session, playback.id, save_position=True)
            return False
        return True

    if playback.mode == "playlist" and status_data.currentplid is not None:
        playlist_map = fetch_playlist_map(playback.http_port, playback.http_password)
        if (
            playback.current_plid is not None
            and status_data.currentplid != playback.current_plid
        ):
            _finalize_current_item(session, playback)
            resolved = resolve_item_from_plid(
                session, playback, status_data.currentplid, playlist_map
            )
            if resolved:
                item_type, item_id = resolved
                playback.current_item_type = item_type
                playback.current_item_id = item_id
                touch_play_started(session, item_type, item_id)

        playback.current_plid = status_data.currentplid
        items = session.exec(
            select(PlaybackSessionItem).where(
                PlaybackSessionItem.session_id == playback.id,
                PlaybackSessionItem.item_id == playback.current_item_id,
            )
        ).all()
        for item in items:
            if item.plid is None:
                item.plid = status_data.currentplid
                session.add(item)

    if playback.current_item_type and playback.current_item_id:
        if settings_store.vlc_resume_playback() and _should_persist_position(status_data):
            update_position(
                session,
                playback.current_item_type,
                playback.current_item_id,
                status_data.time,
                status_data.length,
            )
        if is_playback_complete(status_data):
            mark_completed(session, playback.current_item_type, playback.current_item_id)
            _queue_completion_thumbnail(
                playback.current_item_type, playback.current_item_id
            )

        if settings_store.vlc_resume_playback() and _should_persist_position(status_data):
            playback.last_poll_time = status_data.time
            playback.last_poll_length = status_data.length
            playback.last_poll_position = status_data.position

    session.add(playback)
    session.commit()

    if status_data.state == "stopped" and playback.mode == "single":
        finalize_session(session, playback.id, save_position=True)
        return False

    return True


def _finalize_current_item(session: Session, playback: PlaybackSession) -> None:
    if not playback.current_item_type or not playback.current_item_id:
        return
    time = playback.last_poll_time if playback.last_poll_time is not None else 0
    length = playback.last_poll_length if playback.last_poll_length is not None else 0
    position = playback.last_poll_position if playback.last_poll_position is not None else 0

    if settings_store.vlc_resume_playback():
        update_position(
            session,
            playback.current_item_type,
            playback.current_item_id,
            time,
            length,
        )
    from app.vlc_http import is_playback_complete

    prior = VlcStatus(
        state="playing",
        time=time,
        length=length,
        position=position,
        currentplid=playback.current_plid,
        filename=None,
    )
    if playback.mode == "playlist" or is_playback_complete(prior):
        mark_completed(session, playback.current_item_type, playback.current_item_id)
        _queue_completion_thumbnail(playback.current_item_type, playback.current_item_id)


def _queue_completion_thumbnail(item_type: str, item_id: int) -> None:
    from app.thumbnail_worker import enqueue

    if item_type in ("movie", "episode"):
        enqueue(item_type, item_id)


def get_session_status(session: Session) -> dict | None:
    playback = get_active_session(session)
    if not playback:
        return None
    status = {
        "session_id": playback.id,
        "status": playback.status,
        "mode": playback.mode,
        "current_item_type": playback.current_item_type,
        "current_item_id": playback.current_item_id,
        "started_at": playback.started_at.isoformat() if playback.started_at else None,
    }
    if playback.last_poll_time is not None or playback.last_poll_length is not None:
        status["position_seconds"] = playback.last_poll_time
        status["duration_seconds"] = playback.last_poll_length
        pct = progress_percent(playback.last_poll_time, playback.last_poll_length)
        if pct is not None:
            status["progress_percent"] = pct
        elif playback.last_poll_position is not None:
            status["progress_percent"] = min(
                100.0, round(playback.last_poll_position * 100, 1)
            )
    return status


def resolve_playable(
    session: Session, item_type: str, item_id: int
) -> tuple[str, str | None, str]:
    if item_type == "movie":
        item = session.get(Movie, item_id)
        if not item:
            raise ValueError(f"Movie {item_id} not found")
        return item.file_path, item.subtitle_path, item.title

    if item_type == "episode":
        item = session.get(Episode, item_id)
        if not item:
            raise ValueError(f"Episode {item_id} not found")
        title = f"S{item.season:02d}E{item.episode:02d}"
        return item.file_path, item.subtitle_path, title

    raise ValueError(f"Unknown item type: {item_type}")
