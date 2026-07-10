from datetime import datetime

from sqlmodel import Session, select

from app.models import WatchProgress


def set_watch_status(
    session: Session,
    item_type: str,
    item_id: int,
    watched: bool,
) -> WatchProgress:
    """Create or update watch progress for a movie or episode."""
    progress = session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == item_type,
            WatchProgress.item_id == item_id,
        )
    ).first()

    now = datetime.utcnow()

    if progress:
        progress.watched = watched
        if watched:
            progress.last_watched_at = now
        session.add(progress)
    else:
        progress = WatchProgress(
            item_type=item_type,
            item_id=item_id,
            watched=watched,
            last_watched_at=now if watched else None,
        )
        session.add(progress)

    session.commit()
    return progress


def mark_watched(session: Session, item_type: str, item_id: int) -> WatchProgress:
    """Mark an item as watched and refresh last_watched_at."""
    return set_watch_status(session, item_type, item_id, watched=True)
