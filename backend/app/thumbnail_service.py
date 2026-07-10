import logging

from fastapi import BackgroundTasks
from sqlalchemy import desc
from sqlmodel import Session, select

from app.config import TEST_MODE
from app.thumbnails import needs_poster_regeneration
from app.models import Episode, Movie, Show, WatchProgress
from app.thumbnail_jobs import (
    generate_movie_thumbnail,
    generate_show_thumbnail,
    generate_show_thumbnail_for_show,
)

logger = logging.getLogger(__name__)


def _run_movie_thumbnail(movie_id: int) -> None:
    from app.db import engine
    from sqlmodel import Session as DBSession

    with DBSession(engine) as session:
        generate_movie_thumbnail(session, movie_id)


def _run_show_thumbnail(episode_id: int) -> None:
    from app.db import engine
    from sqlmodel import Session as DBSession

    with DBSession(engine) as session:
        generate_show_thumbnail(session, episode_id)


def _run_episode_hero_thumbnail(episode_id: int) -> None:
    from app.db import engine
    from app.thumbnails import get_or_extract_thumbnail
    from sqlmodel import Session as DBSession

    with DBSession(engine) as session:
        episode = session.get(Episode, episode_id)
        if not episode:
            return
        get_or_extract_thumbnail(episode.file_path, f"episode_{episode.id}")


def queue_hero_thumbnail(hero: dict, background_tasks: BackgroundTasks) -> None:
    if TEST_MODE or not hero:
        return
    if hero.get("item_type") == "episode":
        episode_id = hero.get("episode_id")
        if episode_id:
            background_tasks.add_task(_run_episode_hero_thumbnail, episode_id)
    elif hero.get("item_type") == "movie":
        movie_id = hero.get("id")
        if movie_id:
            background_tasks.add_task(_run_movie_thumbnail, movie_id)


def queue_thumbnail(item_type: str, item_id: int, background_tasks: BackgroundTasks) -> None:
    if TEST_MODE:
        return
    if item_type == "movie":
        background_tasks.add_task(_run_movie_thumbnail, item_id)
    elif item_type == "episode":
        background_tasks.add_task(_run_show_thumbnail, item_id)


def _run_backfill(limit: int) -> None:
    from app.db import engine
    from sqlmodel import Session as DBSession

    with DBSession(engine) as session:
        backfill_watched_thumbnails(session, limit=limit)


def _run_show_poster_for_show(show_id: int) -> None:
    from app.db import engine
    from sqlmodel import Session as DBSession

    with DBSession(engine) as session:
        generate_show_thumbnail_for_show(session, show_id)


def queue_browse_poster_backfill(
    browse_payload: dict,
    background_tasks: BackgroundTasks,
    limit: int = 8,
) -> None:
    """Generate posters for visible browse items that do not have one yet."""
    if TEST_MODE:
        return

    queued = 0
    seen_shows: set[int] = set()
    seen_movies: set[int] = set()

    def queue_show(show_id: int) -> None:
        nonlocal queued
        if show_id in seen_shows or queued >= limit:
            return
        seen_shows.add(show_id)
        background_tasks.add_task(_run_show_poster_for_show, show_id)
        queued += 1

    def queue_movie(movie_id: int) -> None:
        nonlocal queued
        if movie_id in seen_movies or queued >= limit:
            return
        seen_movies.add(movie_id)
        background_tasks.add_task(_run_movie_thumbnail, movie_id)
        queued += 1

    hero = browse_payload.get("hero")
    if hero:
        if not hero.get("thumbnail_url"):
            queue_hero_thumbnail(hero, background_tasks)
        if not hero.get("poster_url"):
            if hero.get("item_type") == "movie":
                queue_movie(hero["id"])
            elif hero.get("item_type") == "episode" and hero.get("show_id"):
                queue_show(hero["show_id"])

    for row in browse_payload.get("rows", []):
        for item in row.get("items", []):
            if queued >= limit:
                return
            if item.get("poster_url"):
                continue
            if item.get("item_type") == "movie":
                queue_movie(item["id"])
            elif item.get("item_type") == "show" or "episode_count" in item:
                queue_show(item["id"])


def queue_watched_thumbnail_backfill(background_tasks: BackgroundTasks, limit: int = 10) -> None:
    if TEST_MODE:
        return
    background_tasks.add_task(_run_backfill, limit)


def backfill_watched_thumbnails(session: Session, limit: int = 10) -> int:
    """Generate thumbnails for watched items that don't have one yet."""
    progress_list = session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == True)  # noqa: E712
        .order_by(desc(WatchProgress.last_watched_at))
    ).all()

    generated = 0
    seen_shows: set[int] = set()

    for progress in progress_list:
        if generated >= limit:
            break

        if progress.item_type == "movie":
            movie = session.get(Movie, progress.item_id)
            if movie and needs_poster_regeneration(movie.poster_path):
                generate_movie_thumbnail(session, movie.id)
                generated += 1

        elif progress.item_type == "episode":
            episode = session.get(Episode, progress.item_id)
            if not episode or episode.show_id in seen_shows:
                continue
            show = session.get(Show, episode.show_id)
            if show and needs_poster_regeneration(show.poster_path):
                generate_show_thumbnail(session, episode.id)
                seen_shows.add(show.id)
                generated += 1

    return generated
