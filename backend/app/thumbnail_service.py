import logging

from fastapi import BackgroundTasks
from sqlalchemy import desc
from sqlmodel import Session, select

from app import settings_store
from app.config import TEST_MODE
from app.models import Episode, Movie, Show, WatchProgress
from app.thumbnail_jobs import (
    generate_movie_thumbnail_standalone,
    generate_show_thumbnail_for_show_standalone,
)
from app.thumbnail_worker import enqueue
from app.thumbnails import needs_poster_regeneration

logger = logging.getLogger(__name__)


def queue_hero_thumbnail(hero: dict, background_tasks: BackgroundTasks) -> None:
    if TEST_MODE or not hero:
        return
    if hero.get("item_type") == "episode":
        episode_id = hero.get("episode_id")
        if episode_id:
            enqueue("episode", episode_id)
    elif hero.get("item_type") == "movie":
        movie_id = hero.get("id")
        if movie_id:
            enqueue("movie", movie_id)


def queue_thumbnail(item_type: str, item_id: int, background_tasks: BackgroundTasks) -> None:
    if TEST_MODE:
        return
    if item_type == "movie":
        enqueue("movie", item_id)
    elif item_type == "episode":
        enqueue("episode", item_id)


def queue_browse_poster_backfill(
    browse_payload: dict,
    background_tasks: BackgroundTasks,
    limit: int = 8,
) -> None:
    """Generate posters for visible browse items that do not have one yet."""
    if TEST_MODE or settings_store.auto_generate_thumbnails():
        return

    queued = 0
    seen_shows: set[int] = set()
    seen_movies: set[int] = set()

    def queue_show(show_id: int) -> None:
        nonlocal queued
        if show_id in seen_shows or queued >= limit:
            return
        seen_shows.add(show_id)
        if enqueue("show_poster", show_id):
            queued += 1

    def queue_movie(movie_id: int) -> None:
        nonlocal queued
        if movie_id in seen_movies or queued >= limit:
            return
        seen_movies.add(movie_id)
        if enqueue("movie", movie_id):
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
    if TEST_MODE or settings_store.auto_generate_thumbnails():
        return
    enqueue("watched", limit)


def backfill_watched_thumbnails(limit: int = 10) -> int:
    """Generate thumbnails for watched items that don't have one yet."""
    import app.db as db

    with Session(db.engine) as session:
        progress_list = session.exec(
            select(WatchProgress)
            .where(WatchProgress.watched == True)  # noqa: E712
            .order_by(desc(WatchProgress.last_watched_at))
        ).all()

        jobs: list[tuple[str, int]] = []
        seen_shows: set[int] = set()

        for progress in progress_list:
            if len(jobs) >= limit:
                break

            if progress.item_type == "movie":
                movie = session.get(Movie, progress.item_id)
                if movie and needs_poster_regeneration(movie.poster_path):
                    jobs.append(("movie", movie.id))

            elif progress.item_type == "episode":
                episode = session.get(Episode, progress.item_id)
                if not episode or episode.show_id in seen_shows:
                    continue
                show = session.get(Show, episode.show_id)
                if show and needs_poster_regeneration(show.poster_path):
                    jobs.append(("show_poster", show.id))
                    seen_shows.add(show.id)

    generated = 0
    for job_type, job_id in jobs:
        if job_type == "movie":
            if generate_movie_thumbnail_standalone(job_id):
                generated += 1
        elif job_type == "show_poster":
            with Session(db.engine) as session:
                if generate_show_thumbnail_for_show_standalone(session, job_id):
                    generated += 1
    return generated


def backfill_library_thumbnails() -> dict:
    """Generate missing movie posters and show tile thumbnails (not episodes)."""
    import app.db as db

    with Session(db.engine) as session:
        movie_ids = [
            movie.id
            for movie in session.exec(select(Movie)).all()
            if needs_poster_regeneration(movie.poster_path)
        ]
        show_ids = [
            show.id
            for show in session.exec(select(Show)).all()
            if needs_poster_regeneration(show.poster_path)
        ]

    stats = {"movies": 0, "shows": 0}
    for movie_id in movie_ids:
        if generate_movie_thumbnail_standalone(movie_id):
            stats["movies"] += 1

    for show_id in show_ids:
        with Session(db.engine) as session:
            if generate_show_thumbnail_for_show_standalone(session, show_id):
                stats["shows"] += 1

    return stats


def backfill_show_episode_thumbnails(session: Session, show_id: int) -> int:
    """Generate missing episode thumbnails for a single show."""
    from app.thumbnail_jobs import generate_episode_thumbnail_standalone

    episode_ids = [
        ep.id
        for ep in session.exec(
            select(Episode)
            .where(Episode.show_id == show_id)
            .order_by(Episode.season, Episode.episode)
        ).all()
        if needs_poster_regeneration(ep.thumbnail_path)
    ]
    generated = 0
    for episode_id in episode_ids:
        if generate_episode_thumbnail_standalone(episode_id):
            generated += 1
    return generated


def queue_all_thumbnails_backfill(
    background_tasks: BackgroundTasks | None = None,
) -> None:
    if TEST_MODE or not settings_store.auto_generate_thumbnails():
        return
    enqueue("library")


def queue_show_episode_thumbnails(
    show_id: int,
    background_tasks: BackgroundTasks,
) -> None:
    """Generate episode thumbnails when a show detail page is opened."""
    if TEST_MODE:
        return
    enqueue("show_episodes", show_id)
