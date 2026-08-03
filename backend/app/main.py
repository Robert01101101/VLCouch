import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session as DBSession

import app.db as db
from app import scan_state, settings_store
from app.config import FRONTEND_DIST, POSTERS_DIR
from app.playback_poller import start_poller, stop_poller
from app.playback_service import sweep_stale_sessions
from app.routers import library, play, settings, watch
from app.thumbnail_service import queue_all_thumbnails_backfill
from app.thumbnail_worker import worker_status
from app.thumbnails import ensure_thumbnail_cache_current_on_startup
from app.update_check import schedule_startup_check

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            scan_state.run_scan(mode="quick")
        else:
            logger.info("Skipping startup scan")
            if settings_store.auto_generate_thumbnails():
                queue_all_thumbnails_backfill()
        asyncio.create_task(schedule_startup_check())
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
    def trigger_scan(
        background_tasks: BackgroundTasks,
        mode: str = Query(default="quick", pattern="^(quick|full)$"),
    ):
        if not scan_state.start_background_scan(background_tasks, mode=mode):
            return {"status": "scan_already_running"}
        return {"status": "scan_started", "mode": mode}

    @application.get("/api/scan/status")
    def scan_status():
        return {
            "running": scan_state.is_scanning(),
            "last_stats": scan_state.last_stats(),
        }

    @application.get("/api/thumbnails/status")
    def thumbnail_status():
        return worker_status()

    @application.get("/api/health")
    def health():
        from app.vlc import VLC_LAUNCH_PROFILE

        return {"status": "ok", "vlc_launch_profile": VLC_LAUNCH_PROFILE}

    if FRONTEND_DIST.exists():
        application.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

    return application


app = create_app()
