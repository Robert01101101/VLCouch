from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.thumbnail_service import queue_thumbnail
from app.watch_service import set_watch_status

router = APIRouter(prefix="/api", tags=["watch"])


class WatchStatusUpdate(BaseModel):
    watched: bool


@router.post("/watch-status/{item_type}/{item_id}")
def update_watch_status(
    item_type: str,
    item_id: int,
    body: WatchStatusUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if item_type not in ("movie", "episode"):
        raise HTTPException(status_code=400, detail="item_type must be 'movie' or 'episode'")

    set_watch_status(session, item_type, item_id, body.watched)

    if body.watched:
        queue_thumbnail(item_type, item_id, background_tasks)

    return {"status": "ok", "watched": body.watched}
