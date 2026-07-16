"""Seed deterministic library data for API tests."""
import json
from datetime import datetime

from sqlmodel import Session

import app.db as db
from app.models import Episode, Movie, Show, WatchProgress

FIXTURE_MOVIE_PATH = "c:/fixtures/movies/The Matrix (1999).mkv"
FIXTURE_EP1_PATH = "c:/fixtures/tv/Breaking Bad/S01E01.mkv"
FIXTURE_EP2_PATH = "c:/fixtures/tv/Breaking Bad/S01E02.mkv"


def seed_library(session: Session | None = None) -> dict:
    """Insert test movies, shows, episodes, and watch progress."""
    owns_session = session is None
    if owns_session:
        session = Session(db.engine)

    movie = Movie(
        title="The Matrix",
        year=1999,
        file_path=FIXTURE_MOVIE_PATH,
        genres=json.dumps(["Sci-Fi", "Action"]),
    )
    session.add(movie)

    show = Show(
        title="Breaking Bad",
        normalized_title="breaking bad",
        category="Drama",
    )
    session.add(show)
    session.flush()

    ep1 = Episode(
        show_id=show.id,
        season=1,
        episode=1,
        title="Pilot",
        file_path=FIXTURE_EP1_PATH,
    )
    ep2 = Episode(
        show_id=show.id,
        season=1,
        episode=2,
        title="Cat's in the Bag...",
        file_path=FIXTURE_EP2_PATH,
    )
    session.add(ep1)
    session.add(ep2)
    session.flush()

    session.add(
        WatchProgress(
            item_type="episode",
            item_id=ep1.id,
            watched=True,
            last_watched_at=datetime(2024, 1, 15, 12, 0, 0),
        )
    )

    session.commit()

    result = {
        "movie_id": movie.id,
        "show_id": show.id,
        "episode_ids": [ep1.id, ep2.id],
    }

    if owns_session:
        session.close()

    return result
