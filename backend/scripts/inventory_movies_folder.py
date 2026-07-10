"""Full recursive inventory of every file under configured movie MEDIA_ROOTS.

Discovers sidecar genre tag files (.txt / .nfo) next to each movie video,
counts genres across the library, and recommends the top 5 for home-page rows.

Usage:
    cd backend
    python scripts/inventory_movies_folder.py

Output (gitignored):
    backend/data/movie_folder_inventory.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Allow `python scripts/inventory_movies_folder.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import MEDIA_ROOTS
from app.genre_tags import TOP_GENRE_ROW_LIMIT, analyze_movie_folders
from app.scanner import VIDEO_EXTENSIONS

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "movie_folder_inventory.json"


def _movie_roots() -> list[Path]:
    return [Path(root["path"]) for root in MEDIA_ROOTS if root.get("type") == "movies"]


def _inventory_root(root: Path) -> dict:
    all_files: list[dict] = []
    by_extension: Counter[str] = Counter()
    dirs_with_videos: dict[str, list[dict]] = defaultdict(list)

    if not root.exists():
        return {
            "root": str(root),
            "exists": False,
            "error": "path does not exist",
            "all_files": [],
            "movie_folders": [],
            "summary": {},
            "genre_analysis": {},
        }

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower() or "(no ext)"
        by_extension[ext] += 1
        try:
            rel = path.relative_to(root)
            parent_rel = str(rel.parent) if rel.parent != Path(".") else ""
        except ValueError:
            rel = path
            parent_rel = ""

        entry = {
            "relative_path": str(rel).replace("\\", "/"),
            "name": path.name,
            "stem": path.stem,
            "extension": ext,
            "parent": parent_rel.replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "is_video": ext in VIDEO_EXTENSIONS,
        }
        all_files.append(entry)
        dirs_with_videos[parent_rel.replace("\\", "/")].append(entry)

    movie_folders: list[dict] = []
    for parent, files in sorted(dirs_with_videos.items()):
        videos = [f for f in files if f["is_video"]]
        if not videos:
            continue
        non_videos = [f for f in files if not f["is_video"]]
        movie_folders.append(
            {
                "folder": parent or ".",
                "video_count": len(videos),
                "videos": [f["name"] for f in videos],
                "other_files": [
                    {"name": f["name"], "extension": f["extension"], "stem": f["stem"]}
                    for f in non_videos
                ],
            }
        )

    sidecar_extensions: Counter[str] = Counter()
    sidecar_stems: Counter[str] = Counter()
    folders_with_sidecars = 0
    for folder in movie_folders:
        if folder["other_files"]:
            folders_with_sidecars += 1
            for other in folder["other_files"]:
                sidecar_extensions[other["extension"]] += 1
                sidecar_stems[other["stem"]] += 1

    genre_counts, tagged_folders, video_total = analyze_movie_folders(movie_folders)
    top_genres = genre_counts.most_common(TOP_GENRE_ROW_LIMIT)

    return {
        "root": str(root),
        "exists": True,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "all_files": all_files,
        "movie_folders": movie_folders,
        "summary": {
            "total_files": len(all_files),
            "total_directories_with_video": len(movie_folders),
            "folders_with_non_video_files": folders_with_sidecars,
            "by_extension": dict(by_extension.most_common()),
            "sidecar_extensions": dict(sidecar_extensions.most_common(30)),
            "top_sidecar_stems": dict(sidecar_stems.most_common(40)),
        },
        "genre_analysis": {
            "tagging_convention": (
                "Sidecar .txt or .nfo in the same folder as the video; "
                "filename format: 'Title - Genre - Genre.txt' (fav and torrent "
                "readme files ignored; casing and dash spacing tolerated)"
            ),
            "video_files": video_total,
            "folders_with_genre_tags": tagged_folders,
            "unique_genres": len(genre_counts),
            "top_genres": [{"genre": g, "count": c} for g, c in top_genres],
            "all_genre_counts": dict(genre_counts.most_common(50)),
        },
    }


def _print_analysis(payload: dict) -> None:
    print("Movie folder inventory")
    print("=" * 60)
    for root_data in payload["roots"]:
        print(f"\nRoot: {root_data['root']}")
        if not root_data.get("exists"):
            print(f"  ERROR: {root_data.get('error', 'missing')}")
            continue
        summary = root_data["summary"]
        print(f"  Total files: {summary['total_files']}")
        print(f"  Directories containing video: {summary['total_directories_with_video']}")
        print(f"  Those with other (non-video) files: {summary['folders_with_non_video_files']}")

        ga = root_data.get("genre_analysis") or {}
        print(f"\n  Genre tagging: {ga.get('tagging_convention', 'unknown')}")
        print(f"  Folders with parsed genre tags: {ga.get('folders_with_genre_tags', 0)}")
        print(f"  Unique genres found: {ga.get('unique_genres', 0)}")
        print(f"\n  Top {TOP_GENRE_ROW_LIMIT} genres (recommended home rows):")
        top = ga.get("top_genres") or []
        if not top:
            print("    (none found)")
        else:
            for rank, entry in enumerate(top, start=1):
                print(f"    {rank}. {entry['genre']}: {entry['count']}")

        print("\n  Extensions (all files):")
        for ext, count in list(summary["by_extension"].items())[:15]:
            print(f"    {ext}: {count}")

        print("\n  Sample tagged folders (up to 10):")
        samples = [
            f
            for f in root_data["movie_folders"]
            if any(
                o["extension"] in {".txt", ".nfo"}
                and " - " in o["stem"]
                for o in f["other_files"]
            )
        ][:10]
        for folder in samples:
            tag_files = [
                o["name"]
                for o in folder["other_files"]
                if o["extension"] in {".txt", ".nfo"} and " - " in o["stem"]
            ]
            print(f"\n    [{folder['folder']}]")
            print(f"      video: {folder['videos'][0] if folder['videos'] else '?'}")
            for name in tag_files[:2]:
                print(f"      tag:   {name}")


def main() -> None:
    roots = _movie_roots()
    if not roots:
        print("No movie MEDIA_ROOTS configured.")
        return

    payload = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "roots": [_inventory_root(root) for root in roots],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote inventory to {OUTPUT_PATH}\n")
    _print_analysis(payload)


if __name__ == "__main__":
    main()
