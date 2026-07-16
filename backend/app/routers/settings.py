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
