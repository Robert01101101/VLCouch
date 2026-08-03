"""Shared library-scan state and orchestration.

Lives outside main.py so other routers (e.g. settings reset-data) can trigger
or inspect scans without importing the FastAPI app module and creating an
import cycle.
"""

import logging
import threading

from fastapi import BackgroundTasks
from sqlmodel import Session as DBSession

import app.db as db
from app import settings_store
from app.library_scan import scan_library
from app.thumbnail_service import queue_all_thumbnails_backfill

logger = logging.getLogger(__name__)

_state: dict = {"running": False, "last_stats": None}
_lock = threading.Lock()


def is_scanning() -> bool:
    return _state["running"]


def last_stats() -> dict | None:
    return _state["last_stats"]


def run_scan(mode: str = "quick") -> None:
    """Run a full-library scan synchronously against all configured media roots."""
    with _lock:
        if not _state["running"]:
            _state["running"] = True
    try:
        logger.info("Starting %s library scan...", mode)
        with DBSession(db.engine) as session:
            stats = scan_library(session, settings_store.media_roots(), limit=0, mode=mode)
        stats["mode"] = mode
        _state["last_stats"] = stats
        logger.info("Scan complete: %s", stats)
        if settings_store.auto_generate_thumbnails():
            queue_all_thumbnails_backfill()
    finally:
        with _lock:
            _state["running"] = False


def start_background_scan(background_tasks: BackgroundTasks, mode: str = "quick") -> bool:
    """Queue a background scan. Returns False if a scan is already running."""
    with _lock:
        if _state["running"]:
            return False
        _state["running"] = True
    background_tasks.add_task(run_scan, mode)
    return True
