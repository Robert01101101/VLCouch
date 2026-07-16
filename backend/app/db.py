from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import DB_PATH


def _sqlite_url(db_path) -> str:
    return f"sqlite:///{Path(db_path).as_posix()}"


engine = create_engine(_sqlite_url(DB_PATH), echo=False)


def override_engine_for_tests(db_path) -> None:
    """Replace the global engine with an isolated test database."""
    global engine
    engine.dispose()
    engine = create_engine(_sqlite_url(db_path), echo=False)


def _migrate_schema() -> None:
    """Lightweight migrations for personal-scale SQLite DB."""
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='show'")
        ).fetchone()
        if not tables:
            return
        show_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(show)"))}
        if "category" not in show_cols:
            conn.execute(text("ALTER TABLE show ADD COLUMN category TEXT"))
            conn.commit()

        movie_tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='movie'")
        ).fetchone()
        if movie_tables:
            movie_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(movie)"))}
            if "genres" not in movie_cols:
                conn.execute(text("ALTER TABLE movie ADD COLUMN genres TEXT"))
                conn.commit()

        wp_tables = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='watchprogress'"
            )
        ).fetchone()
        if wp_tables:
            wp_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(watchprogress)"))}
            if "position_seconds" not in wp_cols:
                conn.execute(text("ALTER TABLE watchprogress ADD COLUMN position_seconds REAL"))
                conn.commit()
            if "duration_seconds" not in wp_cols:
                conn.execute(text("ALTER TABLE watchprogress ADD COLUMN duration_seconds REAL"))
                conn.commit()
            if "last_position_at" not in wp_cols:
                conn.execute(text("ALTER TABLE watchprogress ADD COLUMN last_position_at DATETIME"))
                conn.commit()

        ps_tables = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='playbacksession'"
            )
        ).fetchone()
        if ps_tables:
            ps_cols = {
                row[1] for row in conn.execute(text("PRAGMA table_info(playbacksession)"))
            }
            if "last_poll_time" not in ps_cols:
                conn.execute(text("ALTER TABLE playbacksession ADD COLUMN last_poll_time REAL"))
                conn.commit()
            if "last_poll_length" not in ps_cols:
                conn.execute(text("ALTER TABLE playbacksession ADD COLUMN last_poll_length REAL"))
                conn.commit()
            if "last_poll_position" not in ps_cols:
                conn.execute(
                    text("ALTER TABLE playbacksession ADD COLUMN last_poll_position REAL")
                )
                conn.commit()


def init_db() -> None:
    from app import models  # noqa: F401 — register tables with SQLModel metadata

    SQLModel.metadata.create_all(engine)
    _migrate_schema()


def get_session():
    with Session(engine) as session:
        yield session
