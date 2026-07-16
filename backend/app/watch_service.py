from datetime import datetime

from sqlmodel import Session, select

from app.config import PLAYBACK_MIN_RESUME_SECONDS
from app.models import Episode, WatchProgress


def _get_or_create_progress(
    session: Session, item_type: str, item_id: int
) -> WatchProgress:
    progress = session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == item_type,
            WatchProgress.item_id == item_id,
        )
    ).first()
    if progress:
        return progress
    progress = WatchProgress(item_type=item_type, item_id=item_id)
    session.add(progress)
    return progress


def set_watch_status(
    session: Session,
    item_type: str,
    item_id: int,
    watched: bool,
) -> WatchProgress:
    """Create or update watch progress for a movie or episode."""
    progress = _get_or_create_progress(session, item_type, item_id)

    now = datetime.utcnow()

    progress.watched = watched
    if watched:
        progress.last_watched_at = now
        progress.position_seconds = None
    else:
        progress.position_seconds = None
        progress.duration_seconds = None
        progress.last_position_at = None
    session.add(progress)

    session.commit()
    session.refresh(progress)
    return progress


def mark_watched(session: Session, item_type: str, item_id: int) -> WatchProgress:
    """Mark an item as watched and refresh last_watched_at."""
    return set_watch_status(session, item_type, item_id, watched=True)


def mark_completed(session: Session, item_type: str, item_id: int) -> WatchProgress:
    """Mark playback complete: watched with no resume position."""
    progress = _get_or_create_progress(session, item_type, item_id)
    now = datetime.utcnow()
    progress.watched = True
    progress.last_watched_at = now
    progress.position_seconds = None
    progress.duration_seconds = None
    progress.last_position_at = now
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def update_position(
    session: Session,
    item_type: str,
    item_id: int,
    position: float,
    duration: float,
) -> WatchProgress:
    progress = _get_or_create_progress(session, item_type, item_id)
    progress.position_seconds = max(0.0, position)
    if duration > 0:
        progress.duration_seconds = duration
    progress.last_position_at = datetime.utcnow()
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def touch_play_started(session: Session, item_type: str, item_id: int) -> WatchProgress:
    progress = _get_or_create_progress(session, item_type, item_id)
    progress.last_position_at = datetime.utcnow()
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def get_resume_position(session: Session, item_type: str, item_id: int) -> float | None:
    progress = session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == item_type,
            WatchProgress.item_id == item_id,
        )
    ).first()
    if not progress or progress.watched:
        return None
    if progress.position_seconds is None:
        return None
    if progress.position_seconds < PLAYBACK_MIN_RESUME_SECONDS:
        return None
    return progress.position_seconds


def set_season_watch_status(
    session: Session,
    show_id: int,
    season: int,
    watched: bool,
) -> list[int]:
    """Mark every episode in a season as watched or unwatched."""
    episodes = session.exec(
        select(Episode).where(Episode.show_id == show_id, Episode.season == season)
    ).all()
    if not episodes:
        return []

    now = datetime.utcnow()
    updated_ids: list[int] = []

    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
            )
        ).first()

        if progress:
            progress.watched = watched
            if watched:
                progress.last_watched_at = now
            else:
                progress.position_seconds = None
                progress.duration_seconds = None
                progress.last_position_at = None
            session.add(progress)
        else:
            session.add(
                WatchProgress(
                    item_type="episode",
                    item_id=ep.id,
                    watched=watched,
                    last_watched_at=now if watched else None,
                )
            )
        updated_ids.append(ep.id)

    session.commit()
    return updated_ids


def set_show_watch_status(
    session: Session,
    show_id: int,
    watched: bool,
) -> list[int]:
    """Mark every episode in a show as watched or unwatched."""
    episodes = session.exec(
        select(Episode).where(Episode.show_id == show_id)
    ).all()
    if not episodes:
        return []

    now = datetime.utcnow()
    updated_ids: list[int] = []

    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
            )
        ).first()

        if progress:
            progress.watched = watched
            if watched:
                progress.last_watched_at = now
            else:
                progress.position_seconds = None
                progress.duration_seconds = None
                progress.last_position_at = None
            session.add(progress)
        else:
            session.add(
                WatchProgress(
                    item_type="episode",
                    item_id=ep.id,
                    watched=watched,
                    last_watched_at=now if watched else None,
                )
            )
        updated_ids.append(ep.id)

    session.commit()
    return updated_ids
