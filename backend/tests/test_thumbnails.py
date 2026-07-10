from pathlib import Path

import app.thumbnails as thumbnails
from app.models import Movie
from sqlmodel import Session


def test_pick_seek_seconds_uses_skip_and_percentage(monkeypatch):
    monkeypatch.setattr(thumbnails, "THUMBNAIL_SKIP_SECONDS", 120)
    assert thumbnails._pick_seek_seconds(3600) == 1080
    assert thumbnails._pick_seek_seconds(600) == 180
    assert thumbnails._pick_seek_seconds(None) == 120


def test_pick_seek_seconds_stays_away_from_end(monkeypatch):
    monkeypatch.setattr(thumbnails, "THUMBNAIL_SKIP_SECONDS", 45)
    assert thumbnails._pick_seek_seconds(50) == 20


def test_cache_path_includes_version():
    path = thumbnails._cache_path(Path("D:/Movies/foo.mkv"), "movie_1")
    assert f"_v{thumbnails.THUMBNAIL_CACHE_VERSION}_" in path.name


def test_ensure_thumbnail_cache_current_clears_stale_files_and_db(tmp_path, monkeypatch):
    posters = tmp_path / "posters"
    posters.mkdir()
    monkeypatch.setattr(thumbnails, "POSTERS_DIR", posters)

    stale = posters / "movie_1_old.jpg"
    stale.write_bytes(b"stale")
    (posters / ".cache_version").write_text("1", encoding="utf-8")

    from app import db

    db_path = tmp_path / "test.db"
    db.override_engine_for_tests(db_path)
    db.init_db()

    with Session(db.engine) as session:
        movie = Movie(title="Test", file_path="D:/Movies/test.mkv", poster_path=str(stale))
        session.add(movie)
        session.commit()
        movie_id = movie.id

    assert thumbnails.ensure_thumbnail_cache_current() is True
    assert not stale.exists()
    assert (posters / ".cache_version").read_text(encoding="utf-8") == str(
        thumbnails.THUMBNAIL_CACHE_VERSION
    )

    with Session(db.engine) as session:
        movie = session.get(Movie, movie_id)
        assert movie.poster_path is None

    assert thumbnails.ensure_thumbnail_cache_current() is False


def test_poster_public_url_requires_current_version(tmp_path, monkeypatch):
    posters = tmp_path / "posters"
    posters.mkdir()
    monkeypatch.setattr(thumbnails, "POSTERS_DIR", posters)

    stale = posters / "movie_1_old.jpg"
    stale.write_bytes(b"stale")
    current = posters / f"movie_1_v{thumbnails.THUMBNAIL_CACHE_VERSION}_abc.jpg"
    current.write_bytes(b"current")

    assert thumbnails.poster_public_url(stale) is None
    assert thumbnails.poster_public_url(current) == f"/posters/{current.name}"


def test_reconcile_stale_poster_paths_clears_invalid_db_entries(tmp_path, monkeypatch):
    posters = tmp_path / "posters"
    posters.mkdir()
    monkeypatch.setattr(thumbnails, "POSTERS_DIR", posters)

    stale = posters / "movie_1_old.jpg"
    stale.write_bytes(b"stale")

    from app import db

    db_path = tmp_path / "test.db"
    db.override_engine_for_tests(db_path)
    db.init_db()

    with Session(db.engine) as session:
        movie = Movie(title="Test", file_path="D:/Movies/test.mkv", poster_path=str(stale))
        session.add(movie)
        session.commit()
        movie_id = movie.id

    assert thumbnails.reconcile_stale_poster_paths() == 1

    with Session(db.engine) as session:
        movie = session.get(Movie, movie_id)
        assert movie.poster_path is None
