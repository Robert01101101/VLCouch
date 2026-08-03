import logging
from pathlib import Path

from sqlmodel import Session, select

from app.config import SCAN_LIMIT
from app.genre_tags import extract_movie_genres, serialize_genres
from app.models import Episode, Movie, Show, WatchProgress
from app.scanner import (
    extract_show_title_from_path,
    extract_tv_category,
    is_supplemental_content,
    iter_video_files,
    normalize_title,
    parse_episode,
    parse_movie,
)

logger = logging.getLogger(__name__)

# Batch commits during a scan instead of committing after every file to cut
# down on SQLite fsyncs for large libraries.
COMMIT_BATCH_SIZE = 50


def scan_library(
    session: Session,
    media_roots: list[dict],
    limit: int | None = None,
    mode: str = "quick",
) -> dict:
    """Scan all configured media roots and populate the database.

    ``mode="quick"`` (default) skips guessit re-parsing and sidecar lookups for
    files whose mtime/size match what's already stored. ``mode="full"`` always
    re-parses every file.
    """
    file_limit = limit if limit is not None else (SCAN_LIMIT if SCAN_LIMIT > 0 else None)
    skip_unchanged = mode != "full"
    stats = {
        "movies": 0,
        "episodes": 0,
        "skipped": 0,
        "errors": 0,
        "limit": file_limit,
        "removed": 0,
        "renamed": 0,
        "skipped_unchanged": 0,
    }

    processed = 0
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
                    _upsert_movie(session, video_path, root_path, stats, skip_unchanged)
                elif media_type == "tv":
                    _upsert_episode(session, video_path, root_path, stats, skip_unchanged)
            except Exception as e:
                logger.error("Error processing %s: %s", video_path, e)
                stats["errors"] += 1
            processed += 1
            if processed % COMMIT_BATCH_SIZE == 0:
                session.commit()

    session.commit()

    stats["removed"] = _cleanup_stale_paths(session)
    stats["supplemental_episodes_removed"] = _cleanup_supplemental_episodes(session)
    stats["orphaned_shows_removed"] = _cleanup_orphaned_shows(session)
    return stats


def _stat_file(video_path: Path) -> tuple[float | None, int | None]:
    try:
        file_stat = video_path.stat()
        return file_stat.st_mtime, file_stat.st_size
    except OSError:
        return None, None


def _upsert_movie(
    session: Session,
    video_path: Path,
    movies_root: Path,
    stats: dict,
    skip_unchanged: bool = True,
) -> None:
    file_path = str(video_path)
    mtime, size = _stat_file(video_path)

    existing = session.exec(
        select(Movie).where(Movie.file_path == file_path)
    ).first()

    if existing:
        if (
            skip_unchanged
            and mtime is not None
            and existing.file_mtime == mtime
            and existing.file_size == size
        ):
            stats["skipped_unchanged"] += 1
            return

        parsed = parse_movie(video_path)
        genres = serialize_genres(extract_movie_genres(video_path, movies_root))
        existing.title = parsed["title"]
        existing.year = parsed["year"]
        existing.subtitle_path = parsed["subtitle_path"]
        existing.genres = genres
        existing.file_mtime = mtime
        existing.file_size = size
        session.add(existing)
        return

    parsed = parse_movie(video_path)
    genres = serialize_genres(extract_movie_genres(video_path, movies_root))
    normalized_title = normalize_title(parsed["title"])

    reconciled = None
    for candidate in session.exec(select(Movie).where(Movie.year == parsed["year"])).all():
        if normalize_title(candidate.title) == normalized_title and not Path(
            candidate.file_path
        ).exists():
            reconciled = candidate
            break

    if reconciled:
        reconciled.title = parsed["title"]
        reconciled.file_path = file_path
        reconciled.subtitle_path = parsed["subtitle_path"]
        reconciled.genres = genres
        reconciled.file_mtime = mtime
        reconciled.file_size = size
        session.add(reconciled)
        stats["renamed"] += 1
        return

    movie = Movie(
        title=parsed["title"],
        year=parsed["year"],
        file_path=file_path,
        subtitle_path=parsed["subtitle_path"],
        genres=genres,
        file_mtime=mtime,
        file_size=size,
    )
    session.add(movie)
    stats["movies"] += 1


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


def _cleanup_stale_paths(session: Session) -> int:
    """Delete Movie/Episode rows whose file_path no longer exists on disk."""
    removed = 0
    for movie in session.exec(select(Movie)).all():
        if not Path(movie.file_path).exists():
            _delete_watch_progress(session, "movie", movie.id)
            session.delete(movie)
            removed += 1
    for episode in session.exec(select(Episode)).all():
        if not Path(episode.file_path).exists():
            _delete_watch_progress(session, "episode", episode.id)
            session.delete(episode)
            removed += 1
    if removed:
        session.commit()
    return removed


def _delete_watch_progress(session: Session, item_type: str, item_id: int) -> None:
    for progress in session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == item_type,
            WatchProgress.item_id == item_id,
        )
    ).all():
        session.delete(progress)


def _upsert_episode(
    session: Session,
    video_path: Path,
    tv_root: Path,
    stats: dict,
    skip_unchanged: bool = True,
) -> None:
    if is_supplemental_content(video_path):
        existing = session.exec(
            select(Episode).where(Episode.file_path == str(video_path))
        ).first()
        if existing:
            session.delete(existing)
        stats["skipped"] += 1
        return

    file_path = str(video_path)
    mtime, size = _stat_file(video_path)

    existing = session.exec(
        select(Episode).where(Episode.file_path == file_path)
    ).first()

    if (
        existing
        and skip_unchanged
        and mtime is not None
        and existing.file_mtime == mtime
        and existing.file_size == size
    ):
        stats["skipped_unchanged"] += 1
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
        session.flush()
        session.refresh(show)
    elif category and not show.category:
        show.category = category
        session.add(show)

    if existing:
        existing.show_id = show.id
        existing.season = parsed["season"]
        existing.episode = parsed["episode"]
        existing.title = parsed.get("episode_title")
        existing.subtitle_path = parsed["subtitle_path"]
        existing.file_mtime = mtime
        existing.file_size = size
        session.add(existing)
        return

    reconciled = None
    for candidate in session.exec(
        select(Episode).where(
            Episode.show_id == show.id,
            Episode.season == parsed["season"],
            Episode.episode == parsed["episode"],
        )
    ).all():
        if not Path(candidate.file_path).exists():
            reconciled = candidate
            break

    if reconciled:
        reconciled.file_path = file_path
        reconciled.subtitle_path = parsed["subtitle_path"]
        reconciled.title = parsed.get("episode_title")
        reconciled.file_mtime = mtime
        reconciled.file_size = size
        session.add(reconciled)
        stats["renamed"] += 1
        return

    ep = Episode(
        show_id=show.id,
        season=parsed["season"],
        episode=parsed["episode"],
        title=parsed.get("episode_title"),
        file_path=file_path,
        subtitle_path=parsed["subtitle_path"],
        file_mtime=mtime,
        file_size=size,
    )
    session.add(ep)
    stats["episodes"] += 1
