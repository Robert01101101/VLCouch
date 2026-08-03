"""Movie genre tags from sidecar .txt / .nfo files next to each video.

Discovered tagging convention (movies only — TV category folders are separate):
  Movie Folder/Title (Year) - Genre - Genre.txt
Examples from library inventory:
  17 Again - Comedy.txt
  1917 (2019) - Drama - War - fav.txt
  28 Days Later - Horror.nfo
  8Mile (2002) - drama - biography - music.txt  (casing varies)

Torrent readme .txt files (RARBG, YIFY, etc.) are ignored.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from guessit import guessit
from sqlmodel import Session, select

from app.models import Movie

TAG_FILE_EXTENSIONS = {".txt", ".nfo"}
TOP_GENRE_ROW_LIMIT = 5

DASH_SPLIT_RE = re.compile(r"\s+[-–—]\s+")

NON_GENRE_TAGS = {
    "fav",
    "favourite",
    "favorite",
    "favorites",
    "favourites",
}

# Normalize common casing / spelling mistakes seen in the scan.
GENRE_ALIASES: dict[str, str] = {
    "scifi": "Sci-Fi",
    "sci fi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "sci-fi": "Sci-Fi",
    "animated": "Animation",
    "animation": "Animation",
    "biography": "Biography",
    "biographical": "Biography",
    "romcom": "Rom-Com",
    "rom-com": "Rom-Com",
    "romantic comedy": "Rom-Com",
}

JUNK_STEM_MARKERS = (
    "rarbg",
    "yify",
    "yts.",
    "yts ",
    "torrent",
    "extratorrent",
    "demonoid",
    "ahshare",
    "[tgx]",
    "torrentgalaxy",
    "readme",
    "1337x",
    "silvertorrent",
    "kickass",
    "galaxy.to",
    "upcoming releases",
    "asian torrenz",
    "do_not_mirror",
    "downloaded from",
)


def is_junk_sidecar(stem: str) -> bool:
    lower = stem.lower().strip()
    if not lower or lower in {"info", "i"}:
        return True
    return any(marker in lower for marker in JUNK_STEM_MARKERS)


def normalize_genre(raw: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    if not cleaned:
        return None
    key = cleaned.lower()
    if key in NON_GENRE_TAGS:
        return None
    if key in GENRE_ALIASES:
        return GENRE_ALIASES[key]
    if cleaned.islower() or cleaned.isupper():
        if "-" in cleaned and " " not in cleaned:
            return "-".join(part.capitalize() for part in cleaned.split("-"))
        return cleaned.title()
    return cleaned


def parse_genres_from_tag_stem(stem: str) -> list[str]:
    """Parse genre list from a sidecar tag filename stem."""
    if is_junk_sidecar(stem):
        return []

    parts = DASH_SPLIT_RE.split(stem.strip())
    if len(parts) < 2:
        return []

    genres: list[str] = []
    seen: set[str] = set()
    for raw in parts[1:]:
        # Allow comma-separated genres in one segment: "Action, Thriller"
        for piece in re.split(r"[,/]+", raw):
            genre = normalize_genre(piece)
            if not genre:
                continue
            key = genre.lower()
            if key not in seen:
                seen.add(key)
                genres.append(genre)
    return genres


def _merge_genre_lists(existing: list[str], new: list[str]) -> list[str]:
    seen = {genre.lower() for genre in existing}
    merged = list(existing)
    for genre in new:
        key = genre.lower()
        if key not in seen:
            seen.add(key)
            merged.append(genre)
    return merged


def parse_genres_from_nfo_xml(path: Path) -> list[str]:
    """Parse ``<genre>`` elements from a Plex/Jellyfin-style NFO file."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []

    genres: list[str] = []
    seen: set[str] = set()
    for elem in root.iter("genre"):
        text = (elem.text or "").strip()
        if not text:
            continue
        genre = normalize_genre(text)
        if not genre:
            continue
        key = genre.lower()
        if key in seen:
            continue
        seen.add(key)
        genres.append(genre)
    return genres


def _find_nfo_beside_video(video_path: Path) -> Path | None:
    folder = video_path.parent
    stem = video_path.stem
    for name in (f"{stem}.nfo", "movie.nfo"):
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def extract_dash_sidecar_genres(video_path: Path) -> list[str]:
    tag_file = find_genre_tag_file(video_path)
    if not tag_file:
        return []
    return parse_genres_from_tag_stem(tag_file.stem)


def extract_nfo_xml_genres(video_path: Path) -> list[str]:
    nfo_path = _find_nfo_beside_video(video_path)
    if not nfo_path:
        return []
    return parse_genres_from_nfo_xml(nfo_path)


def extract_folder_tag_genres(video_path: Path) -> list[str]:
    folder = video_path.parent
    if not folder.is_dir():
        return []

    genres: list[str] = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in TAG_FILE_EXTENSIONS:
            continue
        if path.stem == video_path.stem:
            continue
        parsed = parse_genres_from_tag_stem(path.stem)
        if parsed:
            genres = _merge_genre_lists(genres, parsed)
        elif ext == ".nfo":
            genres = _merge_genre_lists(genres, parse_genres_from_nfo_xml(path))
    return genres


def extract_guessit_genres(video_path: Path) -> list[str]:
    info = guessit(video_path.name)
    raw_genres = info.get("genre")
    if not raw_genres:
        return []
    if isinstance(raw_genres, str):
        raw_genres = [raw_genres]
    genres: list[str] = []
    for raw in raw_genres:
        genre = normalize_genre(str(raw))
        if genre:
            genres.append(genre)
    return genres


def extract_show_category_from_folder(show_folder: Path) -> str | None:
    """Category/theme for a show from sidecar tag or NFO files in the show folder."""
    if not show_folder.is_dir():
        return None

    for path in show_folder.iterdir():
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in TAG_FILE_EXTENSIONS:
            genres = parse_genres_from_tag_stem(path.stem)
            if genres:
                return genres[0]
            if ext == ".nfo":
                nfo_genres = parse_genres_from_nfo_xml(path)
                if nfo_genres:
                    return nfo_genres[0]
    return None


def find_genre_tag_file(video_path: Path) -> Path | None:
    """Best sidecar tag file in the same folder as the video."""
    folder = video_path.parent
    if not folder.is_dir():
        return None

    candidates: list[tuple[int, int, Path]] = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in TAG_FILE_EXTENSIONS:
            continue
        genres = parse_genres_from_tag_stem(path.stem)
        if not genres:
            continue
        # Prefer .txt over .nfo; prefer more genres (richer tag file).
        ext_rank = 1 if ext == ".txt" else 0
        candidates.append((ext_rank, len(genres), path))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def extract_movie_genres(
    video_path: Path,
    movies_root: Path | None = None,
    *,
    use_nfo_xml: bool = False,
    use_folder_tags: bool = False,
    use_guessit: bool = False,
) -> list[str]:
    """Extract user genre tags using enabled extractors (dash sidecar always first)."""
    _ = movies_root  # kept for call-site compatibility
    genres = extract_dash_sidecar_genres(video_path)
    if use_nfo_xml:
        genres = _merge_genre_lists(genres, extract_nfo_xml_genres(video_path))
    if use_folder_tags:
        genres = _merge_genre_lists(genres, extract_folder_tag_genres(video_path))
    if use_guessit:
        genres = _merge_genre_lists(genres, extract_guessit_genres(video_path))
    return genres


def analyze_movie_folders(
    movie_folders: list[dict],
) -> tuple[Counter[str], int, int]:
    """Count genres across inventoried movie folders (one tag set per folder)."""
    genre_counts: Counter[str] = Counter()
    tagged_folders = 0
    video_total = 0

    for folder in movie_folders:
        videos = folder.get("videos") or []
        video_total += len(videos)
        folder_path = Path(folder.get("folder") or ".")
        # Reconstruct a representative video path for sibling lookup
        genres: list[str] = []
        if videos:
            fake_video = folder_path / videos[0]
            genres = extract_movie_genres(fake_video)
        if not genres:
            for other in folder.get("other_files") or []:
                ext = other.get("extension", "")
                if ext not in TAG_FILE_EXTENSIONS:
                    continue
                genres = parse_genres_from_tag_stem(other.get("stem", ""))
                if genres:
                    break
        if genres:
            tagged_folders += 1
            for genre in genres:
                genre_counts[genre] += 1

    return genre_counts, tagged_folders, video_total


def serialize_genres(genres: list[str]) -> str | None:
    if not genres:
        return None
    return json.dumps(genres)


def parse_genres_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(genre) for genre in data if genre]
    except json.JSONDecodeError:
        pass
    return []


def genre_row_id(genre: str) -> str:
    slug = re.sub(r"[^\w]+", "-", genre.lower()).strip("-")
    return f"genre-{slug or 'untagged'}"


def top_movie_genres(session: Session, limit: int = TOP_GENRE_ROW_LIMIT) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for movie in session.exec(select(Movie)).all():
        for genre in parse_genres_json(movie.genres):
            counts[genre] += 1
    return counts.most_common(limit)
