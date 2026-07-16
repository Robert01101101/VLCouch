import logging

from sqlmodel import Session, select

from app.models import Episode, Movie, Show
from app.thumbnails import extract_thumbnail, get_or_extract_thumbnail, is_valid_poster_path

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
    episode = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).first()
    if episode:
        generate_show_thumbnail(session, episode.id)


def generate_episode_thumbnail(session: Session, episode_id: int) -> None:
    episode = session.get(Episode, episode_id)
    if not episode:
        return
    if is_valid_poster_path(episode.thumbnail_path):
        return
    thumb = get_or_extract_thumbnail(episode.file_path, f"episode_{episode.id}")
    if thumb:
        episode.thumbnail_path = thumb
        session.add(episode)
        session.commit()


def generate_movie_thumbnail_standalone(movie_id: int) -> bool:
    """Generate a movie poster without holding a DB connection during ffmpeg."""
    import app.db as db

    with Session(db.engine) as session:
        movie = session.get(Movie, movie_id)
        if not movie or is_valid_poster_path(movie.poster_path):
            return False
        file_path = movie.file_path
        cache_key = f"movie_{movie.id}"

    thumb = extract_thumbnail(file_path, cache_key)
    if not thumb:
        return False

    with Session(db.engine) as session:
        movie = session.get(Movie, movie_id)
        if not movie or is_valid_poster_path(movie.poster_path):
            return False
        movie.poster_path = thumb
        session.add(movie)
        session.commit()
    return True


def generate_show_thumbnail_for_show_standalone(session: Session, show_id: int) -> bool:
    """Generate show tile poster; session used only for DB reads/writes, not ffmpeg."""
    episode = session.exec(
        select(Episode)
        .where(Episode.show_id == show_id)
        .order_by(Episode.season, Episode.episode)
    ).first()
    if not episode:
        return False

    show = session.get(Show, episode.show_id)
    if not show or is_valid_poster_path(show.poster_path):
        return False
    file_path = episode.file_path
    cache_key = f"show_{show.id}"

    thumb = extract_thumbnail(file_path, cache_key)
    if not thumb:
        return False

    show = session.get(Show, show_id)
    if not show or is_valid_poster_path(show.poster_path):
        return False
    show.poster_path = thumb
    session.add(show)
    session.commit()
    return True


def generate_episode_thumbnail_standalone(episode_id: int) -> bool:
    """Generate an episode thumbnail without holding a DB connection during ffmpeg."""
    import app.db as db

    with Session(db.engine) as session:
        episode = session.get(Episode, episode_id)
        if not episode or is_valid_poster_path(episode.thumbnail_path):
            return False
        file_path = episode.file_path
        cache_key = f"episode_{episode.id}"

    thumb = get_or_extract_thumbnail(file_path, cache_key)
    if not thumb:
        return False

    with Session(db.engine) as session:
        episode = session.get(Episode, episode_id)
        if not episode or is_valid_poster_path(episode.thumbnail_path):
            return False
        episode.thumbnail_path = thumb
        session.add(episode)
        session.commit()
    return True
