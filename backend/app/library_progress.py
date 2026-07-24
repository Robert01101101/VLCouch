"""Shared watch-progress helpers for browse and playback."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlmodel import Session, select

from app.config import PLAYBACK_MIN_RESUME_SECONDS
from app.models import Episode, WatchProgress


def is_episode_watched(session: Session, episode_id: int) -> bool:
    progress = session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == "episode",
            WatchProgress.item_id == episode_id,
            WatchProgress.watched == True,  # noqa: E712
        )
    ).first()
    return progress is not None


def find_next_unwatched_after(
    session: Session, show_id: int, after_episode: Episode
) -> Episode | None:
    """First unwatched episode after ``after_episode`` in season/episode order."""
    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()
    passed = False
    for ep in episodes:
        if ep.id == after_episode.id:
            passed = True
            continue
        if passed and not is_episode_watched(session, ep.id):
            return ep
    return None


def most_recent_watch(session: Session) -> WatchProgress | None:
    return session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == True)  # noqa: E712
        .where(WatchProgress.last_watched_at.is_not(None))  # type: ignore[union-attr]
        .order_by(desc(WatchProgress.last_watched_at))
    ).first()


def find_in_progress_item(session: Session) -> WatchProgress | None:
    """Most recently updated in-progress item with a meaningful resume position."""
    candidates = session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == False)  # noqa: E712
        .where(WatchProgress.position_seconds.is_not(None))  # type: ignore[union-attr]
        .where(WatchProgress.position_seconds >= PLAYBACK_MIN_RESUME_SECONDS)  # type: ignore[operator]
        .order_by(desc(WatchProgress.last_position_at))
    ).all()
    for progress in candidates:
        if progress.last_position_at is not None:
            return progress
    return candidates[0] if candidates else None


def remaining_unwatched_episodes(
    session: Session,
    show_id: int,
    from_episode: Episode,
) -> list[Episode]:
    """Episodes to play from a user click: that episode first, then later unwatched ones."""
    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()
    result: list[Episode] = []
    started = False
    for ep in episodes:
        if ep.id == from_episode.id:
            started = True
            result.append(ep)
        elif started and not is_episode_watched(session, ep.id):
            result.append(ep)
    return result


def progress_percent(position: float | None, duration: float | None) -> float | None:
    if position is None or duration is None or duration <= 0:
        return None
    return min(100.0, round((position / duration) * 100, 1))


def episode_progress_fields(progress: WatchProgress | None) -> dict:
    if not progress:
        return {
            "position_seconds": None,
            "duration_seconds": None,
            "progress_percent": None,
        }
    return {
        "position_seconds": progress.position_seconds,
        "duration_seconds": progress.duration_seconds,
        "progress_percent": progress_percent(
            progress.position_seconds, progress.duration_seconds
        ),
    }


def most_recent_watched_episode_on_show(
    session: Session, show_id: int
) -> Episode | None:
    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()
    best_episode = None
    best_at: datetime | None = None
    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
                WatchProgress.watched == True,  # noqa: E712
            )
        ).first()
        if progress and progress.last_watched_at and (
            best_at is None or progress.last_watched_at > best_at
        ):
            best_at = progress.last_watched_at
            best_episode = ep
    return best_episode


def find_in_progress_episode_on_show(session: Session, show_id: int) -> Episode | None:
    episodes = session.exec(
        select(Episode).where(Episode.show_id == show_id)
    ).all()
    best_episode = None
    best_at: datetime | None = None
    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
                WatchProgress.watched == False,  # noqa: E712
            )
        ).first()
        if (
            progress
            and progress.position_seconds is not None
            and progress.position_seconds >= PLAYBACK_MIN_RESUME_SECONDS
            and progress.last_position_at
            and (best_at is None or progress.last_position_at > best_at)
        ):
            best_at = progress.last_position_at
            best_episode = ep
    return best_episode
