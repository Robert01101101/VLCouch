"""Single-threaded thumbnail job queue with in-flight deduplication."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Literal

from sqlmodel import Session, select

from app.config import TEST_MODE
from app.models import Episode
from app.thumbnail_jobs import (
    generate_episode_thumbnail_standalone,
    generate_movie_thumbnail_standalone,
    generate_show_thumbnail_for_show_standalone,
)
from app.thumbnails import needs_poster_regeneration

logger = logging.getLogger(__name__)

JobType = Literal["movie", "episode", "show_poster", "show_episodes", "library", "watched"]

_queue: queue.Queue[tuple[JobType, int]] = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()
_in_flight: set[str] = set()
_in_flight_lock = threading.Lock()


def _job_key(job_type: JobType, item_id: int) -> str:
    return f"{job_type}:{item_id}"


def enqueue(job_type: JobType, item_id: int = 0) -> bool:
    """Queue a thumbnail job. Returns False if already queued or running."""
    if TEST_MODE:
        return False
    key = _job_key(job_type, item_id)
    with _in_flight_lock:
        if key in _in_flight:
            return False
        _in_flight.add(key)
    _ensure_worker()
    _queue.put((job_type, item_id))
    return True


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_worker_loop, name="thumbnail-worker", daemon=True)
        _worker.start()


def _worker_loop() -> None:
    while True:
        job_type, item_id = _queue.get()
        key = _job_key(job_type, item_id)
        try:
            _run_job(job_type, item_id)
        except Exception:
            logger.exception("Thumbnail job failed: %s", key)
        finally:
            with _in_flight_lock:
                _in_flight.discard(key)
            _queue.task_done()


def _run_job(job_type: JobType, item_id: int) -> None:
    import app.db as db

    if job_type == "movie":
        generate_movie_thumbnail_standalone(item_id)
        return

    if job_type == "episode":
        generate_episode_thumbnail_standalone(item_id)
        return

    if job_type == "show_poster":
        with Session(db.engine) as session:
            generate_show_thumbnail_for_show_standalone(session, item_id)
        return

    if job_type == "show_episodes":
        with Session(db.engine) as session:
            episode_ids = [
                ep.id
                for ep in session.exec(
                    select(Episode)
                    .where(Episode.show_id == item_id)
                    .order_by(Episode.season, Episode.episode)
                ).all()
                if needs_poster_regeneration(ep.thumbnail_path)
            ]
        generated = 0
        for episode_id in episode_ids:
            if generate_episode_thumbnail_standalone(episode_id):
                generated += 1
        logger.info(
            "Show %d episode thumbnails complete (%d generated)", item_id, generated
        )
        return

    if job_type == "library":
        from app.thumbnail_service import backfill_library_thumbnails

        stats = backfill_library_thumbnails()
        logger.info("Auto thumbnail backfill complete: %s", stats)
        return

    if job_type == "watched":
        from app.thumbnail_service import backfill_watched_thumbnails

        backfill_watched_thumbnails(limit=item_id or 10)
