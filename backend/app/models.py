from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Movie(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    year: Optional[int] = None
    file_path: str = Field(unique=True, index=True)
    subtitle_path: Optional[str] = None
    genres: Optional[str] = None  # JSON list of genres from sidecar .txt/.nfo tag files
    tmdb_id: Optional[int] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None


class Show(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    normalized_title: str = Field(unique=True, index=True)
    category: Optional[str] = Field(default=None, index=True)
    tmdb_id: Optional[int] = None  # legacy, unused
    overview: Optional[str] = None
    poster_path: Optional[str] = None


class Episode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    show_id: int = Field(foreign_key="show.id", index=True)
    season: int
    episode: int
    title: Optional[str] = None
    file_path: str = Field(unique=True, index=True)
    subtitle_path: Optional[str] = None


class WatchProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_type: str = Field(index=True)  # "movie" or "episode"
    item_id: int = Field(index=True)
    watched: bool = False
    last_watched_at: Optional[datetime] = None
