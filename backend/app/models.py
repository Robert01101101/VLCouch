from datetime import datetime

from sqlmodel import Field, SQLModel


class Movie(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    year: int | None = None
    file_path: str = Field(unique=True, index=True)
    subtitle_path: str | None = None
    genres: str | None = None  # JSON list of genres from sidecar .txt/.nfo tag files
    tmdb_id: int | None = None
    overview: str | None = None
    poster_path: str | None = None


class Show(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    normalized_title: str = Field(unique=True, index=True)
    category: str | None = Field(default='Unknown', index=True)  # Updated default
    tmdb_id: int | None = None  # legacy, unused
    overview: str | None = None
    poster_path: str | None = None


class Episode(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    show_id: int = Field(foreign_key="show.id", index=True)
    season: int
    episode: int
    title: str | None = None
    file_path: str = Field(unique=True, index=True)
    subtitle_path: str | None = None
    thumbnail_path: str | None = None


class WatchProgress(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_type: str = Field(index=True)  # "movie" or "episode"
    item_id: int = Field(index=True)
    watched: bool = False
    last_watched_at: datetime | None = None


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str