from collections import defaultdict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc
from sqlmodel import Session, select

from app.config import MEDIA_ROOTS, ROW_ITEM_LIMIT
from app.db import get_session
from app.genre_tags import TOP_GENRE_ROW_LIMIT, genre_row_id, parse_genres_json, top_movie_genres
from app.thumbnail_service import (
    queue_browse_poster_backfill,
    queue_hero_thumbnail,
    queue_watched_thumbnail_backfill,
)
from app.thumbnails import poster_public_url
from app.models import Episode, Movie, Show, WatchProgress
from app.scanner import extract_tv_category, movie_decade

router = APIRouter(prefix="/api", tags=["library"])


def _watch_activity_maps(
    session: Session,
) -> tuple[dict[int, datetime], dict[int, datetime]]:
    """Map movie_id and show_id to most recent play time."""
    by_movie: dict[int, datetime] = {}
    by_show: dict[int, datetime] = {}
    ep_to_show = {
        ep.id: ep.show_id
        for ep in session.exec(select(Episode)).all()
    }
    progress_list = session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == True)  # noqa: E712
        .where(WatchProgress.last_watched_at.is_not(None))  # type: ignore[union-attr]
    ).all()
    for progress in progress_list:
        ts = progress.last_watched_at
        if not ts:
            continue
        if progress.item_type == "movie":
            prev = by_movie.get(progress.item_id)
            if prev is None or ts > prev:
                by_movie[progress.item_id] = ts
        elif progress.item_type == "episode":
            show_id = ep_to_show.get(progress.item_id)
            if show_id is None:
                continue
            prev = by_show.get(show_id)
            if prev is None or ts > prev:
                by_show[show_id] = ts
    return by_movie, by_show


def _row_last_played_at(
    row: dict,
    by_movie: dict[int, datetime],
    by_show: dict[int, datetime],
) -> datetime | None:
    """Most recent play time for any item represented in a browse row."""
    if row["id"] == "recently-watched":
        return None

    best: datetime | None = None
    item_type = row.get("item_type")

    for item in row.get("items", []):
        if item_type == "show" or item.get("item_type") == "show":
            ts = by_show.get(item["id"])
        elif item_type == "movie" or item.get("item_type") == "movie":
            ts = by_movie.get(item["id"])
        else:
            ts = None
        if ts and (best is None or ts > best):
            best = ts
    return best


def _sort_browse_rows_by_play_activity(session: Session, rows: list[dict]) -> list[dict]:
    """Keep Recently Watched first; bubble rows with play history to the top."""
    recent = [row for row in rows if row["id"] == "recently-watched"]
    others = [row for row in rows if row["id"] != "recently-watched"]
    if not others:
        return recent

    by_movie, by_show = _watch_activity_maps(session)

    def sort_key(row: dict) -> tuple[int, float]:
        last_played = _row_last_played_at(row, by_movie, by_show)
        if last_played is None:
            return (1, 0.0)
        return (0, -last_played.timestamp())

    others.sort(key=sort_key)
    return recent + others


def _poster_url(poster_path: str | None) -> str | None:
    return poster_public_url(poster_path)


def _movie_card(movie: Movie) -> dict:
    return {
        "id": movie.id,
        "title": movie.title,
        "year": movie.year,
        "overview": movie.overview,
        "poster_url": _poster_url(movie.poster_path),
        "has_subtitles": movie.subtitle_path is not None,
    }


def _show_card(show: Show, episode_count: int = 0) -> dict:
    return {
        "id": show.id,
        "title": show.title,
        "overview": show.overview,
        "poster_url": _poster_url(show.poster_path),
        "episode_count": episode_count,
        "category": show.category,
    }


@router.get("/movies")
def list_movies(session: Session = Depends(get_session)):
    movies = session.exec(select(Movie).order_by(Movie.title)).all()
    return [_movie_card(m) for m in movies]


@router.get("/shows")
def list_shows(session: Session = Depends(get_session)):
    shows = session.exec(select(Show).order_by(Show.title)).all()
    result = []
    for s in shows:
        episodes = session.exec(
            select(Episode).where(Episode.show_id == s.id)
        ).all()
        result.append(_show_card(s, len(episodes)))
    return result


@router.get("/search")
def search_library(
    q: str = "",
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """Search movies and TV shows by title."""
    query = q.strip()
    if len(query) < 2:
        return {"results": []}

    needle = f"%{query.lower()}%"
    capped = max(1, min(limit, 100))

    movies = session.exec(
        select(Movie).where(Movie.title.ilike(needle)).order_by(Movie.title).limit(capped)
    ).all()
    shows = session.exec(
        select(Show).where(Show.title.ilike(needle)).order_by(Show.title).limit(capped)
    ).all()

    results = []
    for movie in movies:
        card = _movie_card(movie)
        card["item_type"] = "movie"
        results.append(card)

    for show in shows:
        episode_count = len(
            session.exec(select(Episode).where(Episode.show_id == show.id)).all()
        )
        card = _show_card(show, episode_count)
        card["item_type"] = "show"
        results.append(card)

    results.sort(key=lambda item: item["title"].lower())
    return {"results": results[:capped]}


@router.get("/browse")
def browse_home(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Curated home-page rows: recently watched, TV themes, movie decades; hero = up next."""
    _backfill_show_categories(session)
    queue_watched_thumbnail_backfill(background_tasks, limit=5)
    hero = _hero_item(session)
    if hero:
        queue_hero_thumbnail(hero, background_tasks)
    rows = []

    recent_items = _recently_watched_items(session)
    if recent_items:
        rows.append({
            "id": "recently-watched",
            "title": "Recently Watched",
            "item_type": "mixed",
            "items": recent_items,
            "total": len(recent_items),
        })

    # TV shows grouped by folder theme/category
    shows = session.exec(select(Show).order_by(Show.title)).all()
    episode_counts = {
        show.id: len(session.exec(select(Episode).where(Episode.show_id == show.id)).all())
        for show in shows
    }
    by_category: dict[str, list] = defaultdict(list)
    for show in shows:
        category = show.category or "Other TV"
        by_category[category].append(_show_card(show, episode_counts[show.id]))

    for category in sorted(by_category.keys(), key=str.lower):
        items = sorted(by_category[category], key=lambda x: x["title"].lower())
        rows.append({
            "id": f"tv-{category.lower().replace(' ', '-')}",
            "title": category,
            "item_type": "show",
            "items": items[:ROW_ITEM_LIMIT],
            "total": len(items),
        })

    # Movies grouped by decade
    movies = session.exec(select(Movie).order_by(Movie.title)).all()
    by_decade: dict[str, list] = defaultdict(list)
    for movie in movies:
        decade = movie_decade(movie.year) or "Unknown Year"
        by_decade[decade].append(_movie_card(movie))

    def _decade_key(label: str) -> int:
        if label == "Unknown Year":
            return -1
        return int(label.replace("s", ""))

    for decade in sorted(by_decade.keys(), key=_decade_key, reverse=True):
        items = sorted(by_decade[decade], key=lambda x: x["title"].lower())
        rows.append({
            "id": f"movies-{decade}",
            "title": f"{decade} Movies" if decade != "Unknown Year" else "Movies (Unknown Year)",
            "item_type": "movie",
            "items": items[:ROW_ITEM_LIMIT],
            "total": len(items),
        })

    rows = [row for row in rows if row["items"]]

    # Top tagged genres (from sidecar .txt/.nfo files) — inserted after other rows
    genre_rows = []
    for genre, total in top_movie_genres(session, limit=TOP_GENRE_ROW_LIMIT):
        genre_movies = [
            movie for movie in movies if genre in parse_genres_json(movie.genres)
        ]
        items = sorted((_movie_card(movie) for movie in genre_movies), key=lambda x: x["title"].lower())
        if not items:
            continue
        genre_rows.append({
            "id": genre_row_id(genre),
            "title": f"{genre} Movies",
            "item_type": "movie",
            "items": items[:ROW_ITEM_LIMIT],
            "total": total,
        })

    # Recently watched first, then genre rows, then TV/decade rows
    if genre_rows:
        insert_at = 1 if recent_items else 0
        rows[insert_at:insert_at] = genre_rows

    rows = [row for row in rows if row["items"]]
    rows = _sort_browse_rows_by_play_activity(session, rows)

    payload = {"hero": hero, "rows": rows}
    queue_browse_poster_backfill(payload, background_tasks, limit=8)
    return payload


@router.get("/shows/{show_id}")
def get_show(show_id: int, session: Session = Depends(get_session)):
    show = session.get(Show, show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    from app.metadata import enrich_show

    enrich_show(session, show)
    session.refresh(show)

    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()

    seasons: dict[int, list] = {}
    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
            )
        ).first()
        watched = progress.watched if progress else False

        ep_data = {
            "id": ep.id,
            "season": ep.season,
            "episode": ep.episode,
            "title": ep.title,
            "watched": watched,
            "has_subtitles": ep.subtitle_path is not None,
        }
        seasons.setdefault(ep.season, []).append(ep_data)

    season_list = [
        {"season": season_num, "episodes": eps}
        for season_num, eps in sorted(seasons.items())
    ]

    return {
        "id": show.id,
        "title": show.title,
        "overview": show.overview,
        "poster_url": _poster_url(show.poster_path),
        "category": show.category,
        "seasons": season_list,
    }


@router.get("/continue-watching")
def continue_watching(session: Session = Depends(get_session)):
    return _continue_watching_items(session)


def _continue_watching_items(session: Session) -> list[dict]:
    shows = session.exec(select(Show)).all()
    result = []

    for show in shows:
        episodes = session.exec(
            select(Episode).where(Episode.show_id == show.id)
        ).all()
        if not episodes:
            continue

        watched_count = 0
        last_watched_at = None

        for ep in episodes:
            progress = session.exec(
                select(WatchProgress).where(
                    WatchProgress.item_type == "episode",
                    WatchProgress.item_id == ep.id,
                    WatchProgress.watched == True,  # noqa: E712
                )
            ).first()
            if progress:
                watched_count += 1
                if progress.last_watched_at and (
                    last_watched_at is None or progress.last_watched_at > last_watched_at
                ):
                    last_watched_at = progress.last_watched_at

        if 0 < watched_count < len(episodes):
            card = _show_card(show, len(episodes))
            card["watched_count"] = watched_count
            card["total_episodes"] = len(episodes)
            card["last_watched_at"] = (
                last_watched_at.isoformat() if last_watched_at else None
            )
            result.append(card)

    result.sort(key=lambda x: x.get("last_watched_at") or "", reverse=True)
    return result


def _find_up_next_episode(session: Session, show_id: int) -> Episode | None:
    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()
    for ep in episodes:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep.id,
                WatchProgress.watched == True,  # noqa: E712
            )
        ).first()
        if not progress:
            return ep
    return None


def _is_episode_watched(session: Session, episode_id: int) -> bool:
    progress = session.exec(
        select(WatchProgress).where(
            WatchProgress.item_type == "episode",
            WatchProgress.item_id == episode_id,
            WatchProgress.watched == True,  # noqa: E712
        )
    ).first()
    return progress is not None


def _find_next_unwatched_after(
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
        if passed and not _is_episode_watched(session, ep.id):
            return ep
    return None


def _most_recent_watched_episode_on_show(
    session: Session, show_id: int
) -> Episode | None:
    episodes = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).all()
    best_episode = None
    best_at = None
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


def _most_recent_watch(session: Session) -> WatchProgress | None:
    return session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == True)  # noqa: E712
        .where(WatchProgress.last_watched_at.is_not(None))  # type: ignore[union-attr]
        .order_by(desc(WatchProgress.last_watched_at))
    ).first()


def _hero_image_url(
    file_path: str,
    cache_key: str,
    fallback_poster: str | None,
) -> str | None:
    from app.thumbnails import cached_thumbnail_path

    thumb = cached_thumbnail_path(file_path, cache_key)
    if thumb:
        return _poster_url(thumb)
    return _poster_url(fallback_poster)


def _episode_hero(episode: Episode, show: Show, last_watched_at) -> dict:
    return {
        "item_type": "episode",
        "episode_id": episode.id,
        "show_id": show.id,
        "show_title": show.title,
        "season": episode.season,
        "episode": episode.episode,
        "episode_title": episode.title,
        "overview": show.overview,
        "poster_url": _poster_url(show.poster_path),
        "thumbnail_url": _hero_image_url(
            episode.file_path,
            f"episode_{episode.id}",
            show.poster_path,
        ),
        "last_watched_at": last_watched_at.isoformat(),
    }


def _hero_from_continue_watching(session: Session) -> dict | None:
    for card in _continue_watching_items(session):
        show = session.get(Show, card["id"])
        if not show:
            continue
        last_episode = _most_recent_watched_episode_on_show(session, show.id)
        if not last_episode:
            continue
        up_next = _find_next_unwatched_after(session, show.id, last_episode)
        if not up_next:
            continue
        last_at = datetime.utcnow()
        ts = card.get("last_watched_at")
        if ts:
            try:
                last_at = datetime.fromisoformat(ts)
            except ValueError:
                pass
        return _episode_hero(up_next, show, last_at)
    return None


def _hero_item(session: Session) -> dict | None:
    """Hero = up next after the most recently watched item."""
    progress = _most_recent_watch(session)

    if progress:
        if progress.item_type == "movie":
            movie = session.get(Movie, progress.item_id)
            if movie:
                card = _movie_card(movie)
                card["item_type"] = "movie"
                card["thumbnail_url"] = _hero_image_url(
                    movie.file_path,
                    f"movie_{movie.id}",
                    movie.poster_path,
                )
                card["last_watched_at"] = progress.last_watched_at.isoformat()
                return card

        if progress.item_type == "episode":
            last_episode = session.get(Episode, progress.item_id)
            if last_episode:
                show = session.get(Show, last_episode.show_id)
                if show:
                    up_next = _find_next_unwatched_after(
                        session, show.id, last_episode
                    )
                    if up_next:
                        return _episode_hero(up_next, show, progress.last_watched_at)

    return _hero_from_continue_watching(session)


def _recently_watched_items(session: Session) -> list[dict]:
    progress_list = session.exec(
        select(WatchProgress)
        .where(WatchProgress.watched == True)  # noqa: E712
        .order_by(desc(WatchProgress.last_watched_at))
    ).all()

    seen_shows: set[int] = set()
    result: list[dict] = []

    for progress in progress_list:
        if not progress.last_watched_at:
            continue

        if progress.item_type == "movie":
            movie = session.get(Movie, progress.item_id)
            if not movie:
                continue
            card = _movie_card(movie)
            card["item_type"] = "movie"
            card["last_watched_at"] = progress.last_watched_at.isoformat()
            result.append(card)

        elif progress.item_type == "episode":
            episode = session.get(Episode, progress.item_id)
            if not episode or episode.show_id in seen_shows:
                continue
            show = session.get(Show, episode.show_id)
            if not show:
                continue
            seen_shows.add(show.id)
            ep_count = len(
                session.exec(select(Episode).where(Episode.show_id == show.id)).all()
            )
            card = _show_card(show, ep_count)
            card["item_type"] = "show"
            card["last_watched_at"] = progress.last_watched_at.isoformat()
            result.append(card)

        if len(result) >= ROW_ITEM_LIMIT:
            break

    return result


def _tv_root() -> Path | None:
    for root in MEDIA_ROOTS:
        if root.get("type") == "tv":
            return Path(root["path"])
    return None


def _backfill_show_categories(session: Session) -> None:
    """Infer TV folder themes for shows scanned before category support."""
    tv_root = _tv_root()
    if not tv_root:
        return
    shows = session.exec(select(Show).where(Show.category == None)).all()  # noqa: E711
    updated = False
    for show in shows:
        episode = session.exec(
            select(Episode).where(Episode.show_id == show.id)
        ).first()
        if not episode:
            continue
        category = extract_tv_category(Path(episode.file_path), tv_root)
        if category:
            show.category = category
            session.add(show)
            updated = True
    if updated:
        session.commit()
