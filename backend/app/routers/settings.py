from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app import settings_store
from app.db import get_session
from app.thumbnail_service import queue_all_thumbnails_backfill

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsUpdate(BaseModel):
    metadata_enabled: bool | None = None
    scan_on_startup: bool | None = None
    auto_generate_thumbnails: bool | None = None


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
