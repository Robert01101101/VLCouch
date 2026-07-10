import logging
from pathlib import Path

from sqlmodel import Session

from app.models import Episode, Movie, Show
from app.thumbnails import extract_thumbnail, is_valid_poster_path

logger = logging.getLogger(__name__)


def generate_movie_thumbnail(session: Session, movie_id: int) -> None:
    movie = session.get(Movie, movie_id)
    if not movie:
        return
    if is_valid_poster_path(movie.poster_path):
        return
    thumb = extract_thumbnail(movie.file_path, f"movie_{movie.id}")
    if thumb:
        movie.poster_path = thumb
        session.add(movie)
        session.commit()


def generate_show_thumbnail(session: Session, episode_id: int) -> None:
    episode = session.get(Episode, episode_id)
    if not episode:
        return
    show = session.get(Show, episode.show_id)
    if not show:
        return
    if is_valid_poster_path(show.poster_path):
        return
    thumb = extract_thumbnail(episode.file_path, f"show_{show.id}")
    if thumb:
        show.poster_path = thumb
        session.add(show)
        session.commit()


def generate_show_thumbnail_for_show(session: Session, show_id: int) -> None:
    from sqlmodel import select

    episode = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).first()
    if episode:
        generate_show_thumbnail(session, episode.id)
