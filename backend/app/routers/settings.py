from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app import settings_store
from app.config import TEST_MODE
from app.db import get_session
from app.folder_picker import pick_folder
from app.thumbnail_service import queue_all_thumbnails_backfill

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
def get_settings():
    return settings_store.get_settings_payload()


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
    return settings_store.get_settings_payload()


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
    path = pick_folder()
    if not path:
        return {"cancelled": True, "path": None}
    return {"cancelled": False, "path": path}
