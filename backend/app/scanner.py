import re
from pathlib import Path

from guessit import guessit

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".wmv", ".mov", ".m4v", ".webm", ".flv", ".ts"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt", ".sub"}
SUPPLEMENTAL_PATH_PARTS = {
    "featurettes",
    "deleted scenes",
    "samples",
    "sample",
    "extras",
    "bonus",
}


def _single_value(value):
    """guessit sometimes returns a list for season/episode on ambiguous filenames."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def is_supplemental_content(video_path: Path) -> bool:
    """Skip featurettes, deleted scenes, samples, and other non-episode extras."""
    parts = {part.lower() for part in video_path.parts}
    if parts & SUPPLEMENTAL_PATH_PARTS:
        return True
    stem = video_path.stem.lower()
    return stem.endswith(" sample") or stem.endswith("-sample") or "sample.mkv" in video_path.name.lower()


def normalize_title(title: str) -> str:
    """Normalize a show/movie title for deduplication."""
    normalized = title.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def find_subtitle(video_path: Path) -> str | None:
    """Find a subtitle file for a video file."""
    stem = video_path.stem
    parent = video_path.parent

    # Same directory, same base name
    for ext in SUBTITLE_EXTENSIONS:
        candidate = parent / f"{stem}{ext}"
        if candidate.exists():
            return str(candidate)

    # Common Subs subfolder
    for subfolder in ("Subs", "subs", "Subtitles", "subtitles"):
        sub_dir = parent / subfolder
        if sub_dir.is_dir():
            for ext in SUBTITLE_EXTENSIONS:
                candidate = sub_dir / f"{stem}{ext}"
                if candidate.exists():
                    return str(candidate)
            # Any subtitle in the folder matching loosely
            for sub_file in sub_dir.iterdir():
                if sub_file.suffix.lower() in SUBTITLE_EXTENSIONS:
                    if stem.lower() in sub_file.stem.lower() or sub_file.stem.lower() in stem.lower():
                        return str(sub_file)

    return None


def iter_video_files(root: Path, limit: int | None = None):
    """Walk a directory tree and yield video file paths."""
    if not root.exists():
        return
    count = 0
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            yield path
            count += 1
            if limit is not None and limit > 0 and count >= limit:
                return


def _is_category_folder(name: str) -> bool:
    return name.startswith("[") and name.endswith("]")


def extract_tv_category(video_path: Path, tv_root: Path) -> str | None:
    """Extract theme/genre folder from TV library path (e.g. [Modern Comedy...])."""
    try:
        rel = video_path.relative_to(tv_root)
        if len(rel.parts) < 2:
            return None
        category = rel.parts[0]
        if _is_category_folder(category):
            category = category[1:-1]
        return category.strip() or None
    except ValueError:
        return None


def extract_show_title_from_path(video_path: Path, tv_root: Path) -> str | None:
    """Extract show name from TV folder layout: [Category]/ShowName/... or ShowName/..."""
    try:
        rel = video_path.relative_to(tv_root)
        if len(rel.parts) < 2:
            return None
        if _is_category_folder(rel.parts[0]):
            if len(rel.parts) < 3:
                return None
            return rel.parts[1].strip() or None
        return rel.parts[0].strip() or None
    except ValueError:
        return None


def _is_season_folder(name: str) -> bool:
    return bool(re.match(r"^season\s*\d+", name.strip(), re.IGNORECASE))


def resolve_show_folder_path(video_path: Path, tv_roots: list[Path]) -> Path | None:
    """Resolve the on-disk show folder from an episode file path."""
    resolved = video_path.resolve()
    for tv_root in tv_roots:
        try:
            tv_root_resolved = tv_root.resolve()
            rel = resolved.relative_to(tv_root_resolved)
        except ValueError:
            continue

        parts = rel.parts
        if len(parts) < 2:
            continue
        if _is_category_folder(parts[0]):
            if len(parts) < 3:
                continue
            return tv_root_resolved / parts[0] / parts[1]
        return tv_root_resolved / parts[0]

    parent = resolved.parent
    if _is_season_folder(parent.name):
        return parent.parent
    return parent


def movie_decade(year: int | None) -> str | None:
    if not year:
        return None
    decade = (year // 10) * 10
    return f"{decade}s"


def parse_movie(path: Path) -> dict:
    """Parse a movie file path using guessit."""
    info = guessit(path.name)
    title = info.get("title")
    if not title:
        title = path.stem.replace(".", " ")
    return {
        "title": str(title),
        "year": info.get("year"),
        "file_path": str(path),
        "subtitle_path": find_subtitle(path),
    }


def parse_episode(path: Path, show_title_override: str | None = None) -> dict | None:
    """Parse a TV episode file path using guessit."""
    info = guessit(path.name)
    guess_title = info.get("title")
    season = _single_value(info.get("season"))
    episode = _single_value(info.get("episode"))

    if season is None or episode is None:
        return None

    show_title = show_title_override or guess_title
    if not show_title:
        return None

    episode_title = info.get("episode_title")
    if not episode_title and show_title_override and guess_title:
        episode_title = guess_title

    return {
        "show_title": str(show_title),
        "normalized_title": normalize_title(str(show_title)),
        "season": int(season),
        "episode": int(episode),
        "episode_title": str(episode_title) if episode_title else None,
        "file_path": str(path),
        "subtitle_path": find_subtitle(path),
    }
