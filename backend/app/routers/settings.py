import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

import app.db as db
from app import scan_state, settings_store
from app.config import PLAYLISTS_DIR, POSTERS_DIR, TEST_MODE
from app.db import get_session
from app.dependencies import DEPENDENCIES, install_dependency
from app.folder_picker import pick_folder
from app.playback_service import finalize_active_session, get_active_session
from app.thumbnail_service import queue_all_thumbnails_backfill
from app.update_check import check_for_update

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsUpdate(BaseModel):
    metadata_enabled: bool | None = None
    scan_on_startup: bool | None = None
    auto_generate_thumbnails: bool | None = None
    simple_vlc_playback: bool | None = None
    vlc_subtitles_on: bool | None = None
    vlc_resume_playback: bool | None = None
    vlc_tv_playlist: bool | None = None
    vlc_playlist_advance: bool | None = None
    browse_row_random: bool | None = None


class MediaRootEntry(BaseModel):
    path: str
    type: str = Field(pattern="^(movies|tv)$")


class MediaRootsUpdate(BaseModel):
    roots: list[MediaRootEntry]


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)):
    return settings_store.get_settings_payload(session)


@router.get("/update")
async def get_update_status(refresh: bool = False):
    return await check_for_update(force=refresh)


@router.patch("/settings")
def patch_settings(
    body: SettingsUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    was_auto_thumbnails = settings_store.auto_generate_thumbnails()
    if body.metadata_enabled is not None:
        settings_store.set_bool(
            session, settings_store.KEY_METADATA_ENABLED, body.metadata_enabled
        )
    if body.scan_on_startup is not None:
        settings_store.set_bool(
            session, settings_store.KEY_SCAN_ON_STARTUP, body.scan_on_startup
        )
    if body.auto_generate_thumbnails is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_AUTO_GENERATE_THUMBNAILS,
            body.auto_generate_thumbnails,
        )
        if body.auto_generate_thumbnails and not was_auto_thumbnails:
            queue_all_thumbnails_backfill(background_tasks)
    if body.simple_vlc_playback is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_SIMPLE_VLC_PLAYBACK,
            body.simple_vlc_playback,
        )
    if body.vlc_subtitles_on is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_VLC_SUBTITLES_ON,
            body.vlc_subtitles_on,
        )
    if body.vlc_resume_playback is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_VLC_RESUME_PLAYBACK,
            body.vlc_resume_playback,
        )
    if body.vlc_tv_playlist is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_VLC_TV_PLAYLIST,
            body.vlc_tv_playlist,
        )
    if body.vlc_playlist_advance is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_VLC_PLAYLIST_ADVANCE,
            body.vlc_playlist_advance,
        )
    if body.browse_row_random is not None:
        settings_store.set_bool(
            session,
            settings_store.KEY_BROWSE_ROW_RANDOM,
            body.browse_row_random,
        )
    return settings_store.get_settings_payload(session)


@router.get("/media-roots")
def get_media_roots():
    return {"roots": settings_store.media_roots()}


@router.put("/media-roots")
def put_media_roots(body: MediaRootsUpdate, session: Session = Depends(get_session)):
    roots = [entry.model_dump() for entry in body.roots]
    settings_store.set_media_roots(session, roots)
    return {"roots": settings_store.media_roots()}


@router.post("/media-roots/pick-folder")
def pick_media_folder():
    if TEST_MODE:
        raise HTTPException(
            status_code=503,
            detail="Folder picker is not available in test mode",
        )
    result = pick_folder()
    if not result.available:
        return {
            "available": False,
            "cancelled": False,
            "path": None,
            "error": result.error or "Folder picker is not available",
        }
    if result.cancelled or not result.path:
        return {"available": True, "cancelled": True, "path": None}
    return {"available": True, "cancelled": False, "path": result.path}


@router.post("/dependencies/{name}/install")
def install_dependency_package(name: str):
    if name not in DEPENDENCIES:
        raise HTTPException(status_code=400, detail=f"Unknown dependency: {name}")
    if TEST_MODE:
        raise HTTPException(
            status_code=503,
            detail="Dependency installation is not available in test mode",
        )
    try:
        return install_dependency(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _clear_directory_contents(directory: Path) -> None:
    if not directory.exists():
        return
    for entry in directory.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)


@router.post("/settings/reset-data")
def reset_data(background_tasks: BackgroundTasks):
    """Wipe the library database, posters, and playlists, preserving media folders.

    A running scan blocks the reset outright (mid-scan writes would race the
    wipe). An active playback session is instead stopped, since its rows are
    about to be deleted anyway. The pre-wipe session is opened and closed
    explicitly (rather than injected via Depends) so its connection is fully
    released before the engine is disposed and the SQLite file is deleted —
    Windows refuses to delete a file with an open handle.
    """
    if scan_state.is_scanning():
        raise HTTPException(status_code=409, detail="Cannot reset while a scan is running")

    preserved_roots = settings_store.media_roots()

    with Session(db.engine) as session:
        if get_active_session(session):
            finalize_active_session(session, terminate_vlc=True)

    db_file = db.engine.url.database
    db.engine.dispose()
    if db_file:
        Path(db_file).unlink(missing_ok=True)

    _clear_directory_contents(POSTERS_DIR)
    _clear_directory_contents(PLAYLISTS_DIR)

    db.init_db()
    with Session(db.engine) as new_session:
        settings_store.init_settings(new_session)
        if preserved_roots:
            settings_store.set_media_roots(new_session, preserved_roots)

    scan_started = bool(preserved_roots) and scan_state.start_background_scan(
        background_tasks, mode="full"
    )

    return {
        "status": "reset_complete",
        "media_roots_preserved": len(preserved_roots),
        "scan_started": scan_started,
    }
