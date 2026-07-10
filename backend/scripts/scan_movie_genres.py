"""Apply movie genre tags from sidecar files to the library database.

Runs a full movie-folder inventory first, prints the top 5 genres, then
re-scans the library so Movie.genres is populated from .txt/.nfo tag files.

Usage:
    cd backend
    python scripts/scan_movie_genres.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.config import MEDIA_ROOTS
from app.db import engine, init_db
from app.genre_tags import (
    TOP_GENRE_ROW_LIMIT,
    extract_movie_genres,
    parse_genres_json,
    top_movie_genres,
)
from app.library_scan import scan_library
from app.models import Movie

# Reuse inventory scan
from scripts.inventory_movies_folder import OUTPUT_PATH, _inventory_root, _movie_roots, _print_analysis


def main() -> None:
    movie_roots = _movie_roots()
    if not movie_roots:
        print("No movie MEDIA_ROOTS configured.")
        return

    print("Step 1: Full inventory of movies folder(s)\n")
    payload = {
        "roots": [_inventory_root(root) for root in movie_roots],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    import json

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote inventory to {OUTPUT_PATH}\n")
    _print_analysis(payload)

    print("\nStep 2: Re-scan library and store genres on Movie rows\n")
    init_db()
    with Session(engine) as session:
        stats = scan_library(session, MEDIA_ROOTS, limit=0)
        print(f"Scan stats: {stats}")

        movies = session.exec(select(Movie)).all()
        tagged = sum(1 for movie in movies if parse_genres_json(movie.genres))
        print(f"Movies indexed: {len(movies)}")
        print(f"Movies with genre tags: {tagged}")

        top_genres = top_movie_genres(session, limit=TOP_GENRE_ROW_LIMIT)
        print(f"\nTop {TOP_GENRE_ROW_LIMIT} genres in database (home-page rows):")
        if not top_genres:
            print("  (none found)")
        else:
            for rank, (genre, count) in enumerate(top_genres, start=1):
                print(f"  {rank}. {genre}: {count}")

        samples = [
            movie for movie in movies if parse_genres_json(movie.genres)
        ][:5]
        if samples:
            print("\nSample tagged movies:")
            for movie in samples:
                print(f"  - {movie.title}: {parse_genres_json(movie.genres)}")


if __name__ == "__main__":
    main()
