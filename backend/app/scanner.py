import re
from pathlib import Path

from guessit import guessit

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".wmv", ".mov", ".m4v", ".webm", ".flv", ".ts"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt", ".sub"}
SUPPLEMENTAL_PATH_PARTS = {
    "featurettes",
    "featurette",
    "deleted scenes",
    "deleted scene",
    "samples",
    "sample",
    "extras",
    "extra",
    "bonus",
    "bloopers",
    "blooper",
    "outtakes",
    "outtake",
    "behind the scenes",
    "behind-the-scenes",
    "interviews",
    "interview",
    "trailers",
    "trailer",
    "specials",
    "special features",
}
SUPPLEMENTAL_KEYWORDS = (
    "bloopers",
    "blooper",
    "outtakes",
    "outtake",
    "behind the scenes",
    "behind-the-scenes",
    "deleted scene",
    "deleted scenes",
    "featurette",
    "featurettes",
    "interview",
    "trailer",
    "sample",
)
SEASON_FOLDER_RE = re.compile(r"^season\s*(\d+)", re.IGNORECASE)
S_FOLDER_RE = re.compile(r"^s(\d+)$", re.IGNORECASE)
EPISODE_ONLY_RE = re.compile(r"^(\d+)\s*[-–—]\s+")


def _single_value(value):
    """guessit sometimes returns a list for season/episode on ambiguous filenames."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _guessit_info(name: str) -> dict:
    return dict(guessit(name))


def _path_has_supplemental_folder(video_path: Path) -> bool:
    parts = {part.lower() for part in video_path.parts}
    return bool(parts & SUPPLEMENTAL_PATH_PARTS)


def _filename_has_supplemental_keyword(stem: str) -> bool:
    lower = stem.lower()
    return any(keyword in lower for keyword in SUPPLEMENTAL_KEYWORDS)


def _filename_is_sample(stem: str, name: str) -> bool:
    lower_stem = stem.lower()
    lower_name = name.lower()
    return (
        lower_stem.endswith(" sample")
        or lower_stem.endswith("-sample")
        or "sample.mkv" in lower_name
    )


def is_supplemental_path(video_path: Path) -> bool:
    """True when path or filename looks like non-episode extras."""
    if _path_has_supplemental_folder(video_path):
        return True
    stem = video_path.stem
    if _filename_has_supplemental_keyword(stem):
        return True
    return _filename_is_sample(stem, video_path.name)


def classify_tv_content(video_path: Path, strict_supplemental_skip: bool = True) -> str:
    """Return ``skip``, ``supplemental``, or ``episode``."""
    if not is_supplemental_path(video_path):
        return "episode"
    if strict_supplemental_skip:
        return "skip"
    return "supplemental"


def is_supplemental_content(video_path: Path) -> bool:
    """Skip featurettes, deleted scenes, samples, and other non-episode extras."""
    return is_supplemental_path(video_path)


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

    for ext in SUBTITLE_EXTENSIONS:
        candidate = parent / f"{stem}{ext}"
        if candidate.exists():
            return str(candidate)

    for subfolder in ("Subs", "subs", "Subtitles", "subtitles"):
        sub_dir = parent / subfolder
        if sub_dir.is_dir():
            for ext in SUBTITLE_EXTENSIONS:
                candidate = sub_dir / f"{stem}{ext}"
                if candidate.exists():
                    return str(candidate)
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
    return bool(SEASON_FOLDER_RE.match(name.strip()))


def season_from_folder_name(name: str) -> int | None:
    """Parse season number from folder names like Season 01 or S01."""
    stripped = name.strip()
    match = SEASON_FOLDER_RE.match(stripped)
    if match:
        return int(match.group(1))
    match = S_FOLDER_RE.match(stripped)
    if match:
        return int(match.group(1))
    return None


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


def _merge_guessit_info(base: dict, extra: dict) -> dict:
    merged = dict(base)
    for key, value in extra.items():
        if merged.get(key) is None and value is not None:
            merged[key] = value
    return merged


def _resolve_show_title(
    folder_title: str | None,
    guess_title: str | None,
    prefer_folder_show_name: bool,
) -> str | None:
    if prefer_folder_show_name and folder_title:
        return folder_title
    return guess_title or folder_title


def _resolve_episode_title(
    info: dict,
    show_title: str,
    folder_title: str | None,
    prefer_folder_show_name: bool,
    fallback_stem: str | None = None,
) -> str | None:
    episode_title = info.get("episode_title")
    guess_title = info.get("title")
    if episode_title:
        return str(episode_title)
    if prefer_folder_show_name and folder_title and guess_title and guess_title != show_title:
        return str(guess_title)
    if fallback_stem:
        return fallback_stem
    return None


def parse_episode_context(
    video_path: Path,
    tv_root: Path,
    *,
    prefer_folder_show_name: bool = True,
    parse_tv_from_path: bool = False,
    strict_supplemental_skip: bool = True,
) -> dict | None:
    """Parse a TV file with folder, path, and filename context."""
    classification = classify_tv_content(video_path, strict_supplemental_skip)
    if classification == "skip":
        return None

    episode_kind = "supplemental" if classification == "supplemental" else "episode"
    info = _guessit_info(video_path.name)

    if parse_tv_from_path:
        try:
            rel = video_path.relative_to(tv_root)
            info = _merge_guessit_info(info, _guessit_info(rel.as_posix()))
        except ValueError:
            pass

    season = _single_value(info.get("season"))
    episode = _single_value(info.get("episode"))

    parent_season = season_from_folder_name(video_path.parent.name)
    if season is None and parent_season is not None:
        season = parent_season

    if season is None and episode is not None:
        only_episode = EPISODE_ONLY_RE.match(video_path.stem)
        if only_episode:
            season = 1

    if episode_kind == "episode" and season is None:
        only_episode = EPISODE_ONLY_RE.match(video_path.stem)
        if only_episode and episode is None:
            episode = int(only_episode.group(1))
            season = parent_season or 1

    if episode_kind == "episode" and (season is None or episode is None):
        return None

    folder_title = extract_show_title_from_path(video_path, tv_root)
    show_title = _resolve_show_title(
        folder_title,
        info.get("title"),
        prefer_folder_show_name,
    )
    if not show_title:
        return None

    if episode_kind == "supplemental" and season is None:
        season = 0

    episode_title = _resolve_episode_title(
        info,
        show_title,
        folder_title,
        prefer_folder_show_name,
        fallback_stem=video_path.stem if episode_kind == "supplemental" else None,
    )

    return {
        "show_title": str(show_title),
        "normalized_title": normalize_title(str(show_title)),
        "season": int(season) if season is not None else None,
        "episode": int(episode) if episode is not None else None,
        "episode_title": episode_title,
        "file_path": str(video_path),
        "subtitle_path": find_subtitle(video_path),
        "episode_kind": episode_kind,
    }


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
    info = _guessit_info(path.name)
    guess_title = info.get("title")
    season = _single_value(info.get("season"))
    episode = _single_value(info.get("episode"))

    if season is None:
        parent_season = season_from_folder_name(path.parent.name)
        if parent_season is not None:
            season = parent_season

    if season is None or episode is None:
        only_episode = EPISODE_ONLY_RE.match(path.stem)
        if only_episode:
            if episode is None:
                episode = int(only_episode.group(1))
            if season is None:
                season = season_from_folder_name(path.parent.name) or 1

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
        "episode_kind": "episode",
    }
