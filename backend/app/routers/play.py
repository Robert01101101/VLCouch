from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db import get_session
from app.playback_service import get_session_status
from app.vlc import play_item

router = APIRouter(prefix="/api", tags=["play"])


@router.post("/play/{item_type}/{item_id}")
def play(
    item_type: str,
    item_id: int,
    from_start: bool = Query(default=False),
    session: Session = Depends(get_session),
):
    if item_type not in ("movie", "episode"):
        raise HTTPException(status_code=400, detail="item_type must be 'movie' or 'episode'")
    try:
        result = play_item(session, item_type, item_id, from_start=from_start)
        return {"status": "ok", **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/playback/session")
def playback_session(session: Session = Depends(get_session)):
    status = get_session_status(session)
    if not status:
        return {"active": False}
    return {"active": True, **status}
