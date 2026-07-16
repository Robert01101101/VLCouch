import logging
from pathlib import Path

from sqlmodel import Session, select

from app.config import SCAN_LIMIT
from app.genre_tags import extract_movie_genres, serialize_genres
from app.models import Episode, Movie, Show
from app.scanner import (
    extract_show_title_from_path,
    extract_tv_category,
    is_supplemental_content,
    iter_video_files,
    parse_episode,
    parse_movie,
)

logger = logging.getLogger(__name__)


def scan_library(session: Session, media_roots: list[dict], limit: int | None = None) -> dict:
    """Scan all configured media roots and populate the database."""
    file_limit = limit if limit is not None else (SCAN_LIMIT if SCAN_LIMIT > 0 else None)
    stats = {"movies": 0, "episodes": 0, "skipped": 0, "errors": 0, "limit": file_limit}

    for root_config in media_roots:
        root_path = Path(root_config["path"])
        media_type = root_config.get("type", "movies")

        if not root_path.exists():
            logger.warning("Media root does not exist: %s", root_path)
            continue

        if file_limit:
            logger.info("Scanning %s (limit: %d files)", root_path, file_limit)
        else:
            logger.info("Scanning %s (no limit)", root_path)

        for video_path in iter_video_files(root_path, limit=file_limit):
            try:
                if media_type == "movies":
                    _upsert_movie(session, video_path, root_path, stats)
                elif media_type == "tv":
                    _upsert_episode(session, video_path, root_path, stats)
            except Exception as e:
                logger.error("Error processing %s: %s", video_path, e)
                stats["errors"] += 1

    stats["orphaned_shows_removed"] = _cleanup_orphaned_shows(session)
    stats["supplemental_episodes_removed"] = _cleanup_supplemental_episodes(session)
    return stats


def _upsert_movie(
    session: Session, video_path: Path, movies_root: Path, stats: dict
) -> None:
    parsed = parse_movie(video_path)
    genres = serialize_genres(extract_movie_genres(video_path, movies_root))
    existing = session.exec(
        select(Movie).where(Movie.file_path == parsed["file_path"])
    ).first()

    if existing:
        existing.title = parsed["title"]
        existing.year = parsed["year"]
        existing.subtitle_path = parsed["subtitle_path"]
        existing.genres = genres
        session.add(existing)
    else:
        movie = Movie(
            title=parsed["title"],
            year=parsed["year"],
            file_path=parsed["file_path"],
            subtitle_path=parsed["subtitle_path"],
            genres=genres,
        )
        session.add(movie)
        stats["movies"] += 1

    session.commit()


def _cleanup_orphaned_shows(session: Session) -> int:
    """Remove shows left behind after episodes were reassigned to the correct show."""
    removed = 0
    for show in session.exec(select(Show)).all():
        episode_count = len(
            session.exec(select(Episode).where(Episode.show_id == show.id)).all()
        )
        if episode_count == 0:
            session.delete(show)
            removed += 1
    if removed:
        session.commit()
    return removed


def _cleanup_supplemental_episodes(session: Session) -> int:
    """Remove episodes indexed from featurettes/deleted scenes before skip logic existed."""
    removed = 0
    for episode in session.exec(select(Episode)).all():
        if is_supplemental_content(Path(episode.file_path)):
            session.delete(episode)
            removed += 1
    if removed:
        session.commit()
    return removed


def _upsert_episode(
    session: Session, video_path: Path, tv_root: Path, stats: dict
) -> None:
    if is_supplemental_content(video_path):
        existing = session.exec(
            select(Episode).where(Episode.file_path == str(video_path))
        ).first()
        if existing:
            session.delete(existing)
            session.commit()
        stats["skipped"] += 1
        return

    folder_title = extract_show_title_from_path(video_path, tv_root)
    parsed = parse_episode(video_path, show_title_override=folder_title)
    if not parsed:
        stats["skipped"] += 1
        return

    category = extract_tv_category(video_path, tv_root)

    show = session.exec(
        select(Show).where(Show.normalized_title == parsed["normalized_title"])
    ).first()

    if not show:
        show = Show(
            title=parsed["show_title"],
            normalized_title=parsed["normalized_title"],
            category=category,
        )
        session.add(show)
        session.commit()
        session.refresh(show)
    elif category and not show.category:
        show.category = category
        session.add(show)
        session.commit()

    existing = session.exec(
        select(Episode).where(Episode.file_path == parsed["file_path"])
    ).first()

    if existing:
        existing.show_id = show.id
        existing.season = parsed["season"]
        existing.episode = parsed["episode"]
        existing.title = parsed.get("episode_title")
        existing.subtitle_path = parsed["subtitle_path"]
        session.add(existing)
    else:
        ep = Episode(
            show_id=show.id,
            season=parsed["season"],
            episode=parsed["episode"],
            title=parsed.get("episode_title"),
            file_path=parsed["file_path"],
            subtitle_path=parsed["subtitle_path"],
        )
        session.add(ep)
        stats["episodes"] += 1

    session.commit()
