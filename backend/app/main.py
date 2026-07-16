import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session as DBSession

import app.db as db
from app import settings_store
from app.config import FRONTEND_DIST, POSTERS_DIR
from app.library_scan import scan_library
from app.playback_poller import start_poller, stop_poller
from app.playback_service import sweep_stale_sessions
from app.routers import library, play, settings, watch
from app.thumbnail_service import queue_all_thumbnails_backfill
from app.thumbnails import ensure_thumbnail_cache_current_on_startup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scan_state: dict = {"running": False, "last_stats": None}


def _run_scan():
    from sqlmodel import Session as DBSession

    _scan_state["running"] = True
    try:
        logger.info("Starting full library scan (no file limit)...")
        with DBSession(db.engine) as session:
            stats = scan_library(session, settings_store.media_roots(), limit=0)
        _scan_state["last_stats"] = stats
        logger.info("Scan complete: %s", stats)
        if settings_store.auto_generate_thumbnails():
            queue_all_thumbnails_backfill()
    finally:
        _scan_state["running"] = False


def create_app(*, lifespan_scan: bool | None = None) -> FastAPI:
    """Create a FastAPI app. Tests pass lifespan_scan=False to skip startup scan."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.init_db()
        with DBSession(db.engine) as session:
            settings_store.init_settings(session)
        ensure_thumbnail_cache_current_on_startup()
        sweep_stale_sessions()
        start_poller()
        should_scan = (
            settings_store.scan_on_startup()
            if lifespan_scan is None
            else lifespan_scan
        )
        if should_scan:
            _run_scan()
        else:
            logger.info("Skipping startup scan")
            if settings_store.auto_generate_thumbnails():
                queue_all_thumbnails_backfill()
        yield
        stop_poller()

    application = FastAPI(title="VLCouch", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(library.router)
    application.include_router(play.router)
    application.include_router(settings.router)
    application.include_router(watch.router)

    application.mount("/posters", StaticFiles(directory=str(POSTERS_DIR)), name="posters")

    @application.post("/api/scan")
    def trigger_scan(background_tasks: BackgroundTasks):
        if _scan_state["running"]:
            return {"status": "scan_already_running"}
        background_tasks.add_task(_run_scan)
        return {"status": "scan_started"}

    @application.get("/api/scan/status")
    def scan_status():
        return {
            "running": _scan_state["running"],
            "last_stats": _scan_state["last_stats"],
        }

    @application.get("/api/health")
    def health():
        from app.vlc import VLC_LAUNCH_PROFILE

        return {"status": "ok", "vlc_launch_profile": VLC_LAUNCH_PROFILE}

    if FRONTEND_DIST.exists():
        application.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

    return application


app = create_app()
