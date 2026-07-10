import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import FRONTEND_DIST, MEDIA_ROOTS, POSTERS_DIR, SCAN_ON_STARTUP
from app.thumbnails import ensure_thumbnail_cache_current_on_startup
from app.db import init_db
from app.library_scan import scan_library
from app.routers import library, play, watch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scan_state: dict = {"running": False, "last_stats": None}


def _run_scan():
    from app.db import engine
    from sqlmodel import Session as DBSession

    _scan_state["running"] = True
    try:
        logger.info("Starting full library scan (no file limit)...")
        with DBSession(engine) as session:
            stats = scan_library(session, MEDIA_ROOTS, limit=0)
        _scan_state["last_stats"] = stats
        logger.info("Scan complete: %s", stats)
    finally:
        _scan_state["running"] = False


def create_app(*, lifespan_scan: bool | None = None) -> FastAPI:
    """Create a FastAPI app. Tests pass lifespan_scan=False to skip startup scan."""
    scan_on_startup = SCAN_ON_STARTUP if lifespan_scan is None else lifespan_scan

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        ensure_thumbnail_cache_current_on_startup()
        if scan_on_startup:
            _run_scan()
        else:
            logger.info("Skipping startup scan")
        yield

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
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        application.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

    return application


app = create_app()
