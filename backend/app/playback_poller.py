"""Background poller for active VLC playback sessions."""

from __future__ import annotations

import logging
import threading

from sqlmodel import Session, select

import app.db as db
from app.config import PLAYBACK_POLL_INTERVAL_SECONDS, TEST_MODE
from app.models import PlaybackSession
from app.playback_service import poll_session

logger = logging.getLogger(__name__)

_worker: threading.Thread | None = None
_worker_lock = threading.Lock()
_stop_event = threading.Event()


def start_poller() -> None:
    if TEST_MODE:
        return
    with _worker_lock:
        global _worker
        if _worker and _worker.is_alive():
            return
        _stop_event.clear()
        _worker = threading.Thread(target=_poll_loop, daemon=True, name="playback-poller")
        _worker.start()


def stop_poller() -> None:
    _stop_event.set()


def _poll_loop() -> None:
    while not _stop_event.is_set():
        try:
            with Session(db.engine) as session:
                active = session.exec(
                    select(PlaybackSession).where(PlaybackSession.status == "active")
                ).all()
                for playback in active:
                    poll_session(session, playback.id)
        except Exception:
            logger.exception("Playback poller tick failed")
        _stop_event.wait(PLAYBACK_POLL_INTERVAL_SECONDS)


def tick_once(session_id: str) -> bool:
    """Test helper: run one poll cycle for a session."""
    with Session(db.engine) as session:
        return poll_session(session, session_id)
