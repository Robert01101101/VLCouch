from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Episode, Show
from app.thumbnail_service import queue_thumbnail
from app.watch_service import set_season_watch_status, set_watch_status

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


@router.post("/shows/{show_id}/seasons/{season}/watch-status")
def update_season_watch_status(
    show_id: int,
    season: int,
    body: WatchStatusUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    show = session.get(Show, show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    has_season = session.exec(
        select(Episode.id).where(Episode.show_id == show_id, Episode.season == season)
    ).first()
    if not has_season:
        raise HTTPException(status_code=404, detail="Season not found")

    episode_ids = set_season_watch_status(session, show_id, season, body.watched)

    if body.watched:
        for episode_id in episode_ids:
            queue_thumbnail("episode", episode_id, background_tasks)

    return {"status": "ok", "watched": body.watched, "updated_count": len(episode_ids)}
