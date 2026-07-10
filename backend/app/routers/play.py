from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.thumbnail_service import queue_thumbnail
from app.vlc import play_item
from app.watch_service import mark_watched

router = APIRouter(prefix="/api", tags=["play"])


@router.post("/play/{item_type}/{item_id}")
def play(
    item_type: str,
    item_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if item_type not in ("movie", "episode"):
        raise HTTPException(status_code=400, detail="item_type must be 'movie' or 'episode'")
    try:
        result = play_item(session, item_type, item_id)
        mark_watched(session, item_type, item_id)
        queue_thumbnail(item_type, item_id, background_tasks)
        return {"status": "ok", **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
