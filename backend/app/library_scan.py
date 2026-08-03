import logging
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, select

from app.config import SCAN_LIMIT
from app.genre_tags import extract_movie_genres, extract_show_category_from_folder, serialize_genres
from app.models import Episode, Movie, Show, WatchProgress
from app.scan_config import (
    INDEX_BONUS_CONTENT,
    PARSE_TV_FROM_PATH,
    USE_GENRE_FOLDER_TAGS,
    USE_GENRE_GUESSIT,
    USE_GENRE_NFO_XML,
)
from app.scanner import (
    classify_tv_content,
    is_supplemental_path,
    iter_video_files,
    normalize_title,
    parse_episode_context,
    parse_movie,
    resolve_show_folder_path,
)

logger = logging.getLogger(__name__)

COMMIT_BATCH_SIZE = 50


def scan_library(
    session: Session,
    media_roots: list[dict],
    limit: int | None = None,
    mode: str = "quick",
) -> dict:
    """Scan all configured media roots and populate the database."""
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


def _genre_options() -> dict:
    return {
        "use_nfo_xml": USE_GENRE_NFO_XML,
        "use_folder_tags": USE_GENRE_FOLDER_TAGS,
        "use_guessit": USE_GENRE_GUESSIT,
    }


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

    genre_kwargs = _genre_options()

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
        genres = serialize_genres(extract_movie_genres(video_path, movies_root, **genre_kwargs))
        existing.title = parsed["title"]
        existing.year = parsed["year"]
        existing.subtitle_path = parsed["subtitle_path"]
        existing.genres = genres
        existing.file_mtime = mtime
        existing.file_size = size
        session.add(existing)
        return

    parsed = parse_movie(video_path)
    genres = serialize_genres(extract_movie_genres(video_path, movies_root, **genre_kwargs))
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
    """Remove legacy episode rows indexed from bonus-content paths before indexing was enabled."""
    if INDEX_BONUS_CONTENT:
        return 0
    removed = 0
    for episode in session.exec(select(Episode)).all():
        path = Path(episode.file_path)
        if episode.episode_kind == "supplemental" or is_supplemental_path(path):
            session.delete(episode)
            removed += 1
    if removed:
        session.commit()
    return removed


def _cleanup_stale_paths(session: Session) -> int:
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


def _next_supplemental_episode_number(session: Session, show_id: int) -> int:
    max_episode = session.exec(
        select(func.max(Episode.episode)).where(
            Episode.show_id == show_id,
            Episode.season == 0,
            Episode.episode_kind == "supplemental",
        )
    ).one()
    return (max_episode or 0) + 1


def _resolve_tv_category(
    session: Session,
    video_path: Path,
    tv_root: Path,
    show: Show | None,
) -> str | None:
    from app.scanner import extract_tv_category

    bracket_category = extract_tv_category(video_path, tv_root)
    if bracket_category:
        return bracket_category

    show_folder = resolve_show_folder_path(video_path, [tv_root])
    if show_folder:
        folder_category = extract_show_category_from_folder(show_folder)
        if folder_category:
            return folder_category

    if show and show.category and show.category != "Unknown":
        return show.category
    return None


def _upsert_episode(
    session: Session,
    video_path: Path,
    tv_root: Path,
    stats: dict,
    skip_unchanged: bool = True,
) -> None:
    classification = classify_tv_content(
        video_path,
        strict_supplemental_skip=not INDEX_BONUS_CONTENT,
    )
    if classification == "skip":
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

    parsed = parse_episode_context(
        video_path,
        tv_root,
        prefer_folder_show_name=True,
        parse_tv_from_path=PARSE_TV_FROM_PATH,
        strict_supplemental_skip=not INDEX_BONUS_CONTENT,
    )
    if not parsed:
        stats["skipped"] += 1
        return

    show = session.exec(
        select(Show).where(Show.normalized_title == parsed["normalized_title"])
    ).first()

    category = _resolve_tv_category(session, video_path, tv_root, show)

    if not show:
        show = Show(
            title=parsed["show_title"],
            normalized_title=parsed["normalized_title"],
            category=category,
        )
        session.add(show)
        session.flush()
        session.refresh(show)
    elif category and (not show.category or show.category == "Unknown"):
        show.category = category
        session.add(show)

    episode_kind = parsed.get("episode_kind", "episode")
    season = parsed["season"]
    episode_num = parsed["episode"]

    if episode_kind == "supplemental" and episode_num is None:
        episode_num = _next_supplemental_episode_number(session, show.id)

    if season is None or episode_num is None:
        stats["skipped"] += 1
        return

    if existing:
        existing.show_id = show.id
        existing.season = season
        existing.episode = episode_num
        existing.title = parsed.get("episode_title")
        existing.subtitle_path = parsed["subtitle_path"]
        existing.episode_kind = episode_kind
        existing.file_mtime = mtime
        existing.file_size = size
        session.add(existing)
        return

    reconciled = None
    if episode_kind == "episode":
        for candidate in session.exec(
            select(Episode).where(
                Episode.show_id == show.id,
                Episode.season == season,
                Episode.episode == episode_num,
                Episode.episode_kind == "episode",
            )
        ).all():
            if not Path(candidate.file_path).exists():
                reconciled = candidate
                break

    if reconciled:
        reconciled.file_path = file_path
        reconciled.subtitle_path = parsed["subtitle_path"]
        reconciled.title = parsed.get("episode_title")
        reconciled.episode_kind = episode_kind
        reconciled.file_mtime = mtime
        reconciled.file_size = size
        session.add(reconciled)
        stats["renamed"] += 1
        return

    ep = Episode(
        show_id=show.id,
        season=season,
        episode=episode_num,
        title=parsed.get("episode_title"),
        file_path=file_path,
        subtitle_path=parsed["subtitle_path"],
        episode_kind=episode_kind,
        file_mtime=mtime,
        file_size=size,
    )
    session.add(ep)
    stats["episodes"] += 1
