"""M3U playlist builder for VLC binge sessions."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
from urllib.parse import quote

from app.models import Episode


def path_to_file_uri(path: str) -> str:
    """Convert a Windows path to a file:/// URI."""
    normalized = PureWindowsPath(path).as_posix()
    if normalized.startswith("//"):
        return "file:" + quote(normalized, safe="/:")
    return "file:///" + quote(normalized, safe="/:")


def build_m3u(
    episodes: list[Episode],
    *,
    start_times: dict[int, float] | None = None,
    subtitles_on: bool = False,
) -> str:
    """Build M3U content for VLC binge playlists with per-item resume options."""
    resume = start_times or {}
    lines = ["#EXTM3U"]
    for ep in episodes:
        label = f"S{ep.season:02d}E{ep.episode:02d}"
        if ep.title:
            label = f"{label} - {ep.title}"
        lines.append(f"#EXTINF:-1,{label}")
        start = resume.get(ep.id)
        if start and start > 0:
            lines.append(f"#EXTVLCOPT:start-time={start}")
        if ep.subtitle_path and Path(ep.subtitle_path).exists():
            lines.append(f"#EXTVLCOPT:sub-file={path_to_file_uri(ep.subtitle_path)}")
        if subtitles_on:
            lines.append("#EXTVLCOPT:sub-track=0")
        lines.append(path_to_file_uri(ep.file_path))
    return "\n".join(lines) + "\n"
