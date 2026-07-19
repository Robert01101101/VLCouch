from pathlib import Path

from sqlmodel import Session, select

import app.db as db
from app.config import MEDIA_ROOTS
from app.library_scan import scan_library
from app.models import Episode, Movie, Show
from app.scanner import (
    extract_show_title_from_path,
    is_supplemental_content,
    parse_episode,
    resolve_show_folder_path,
)


def test_scan_library_fixture_media(empty_client, tmp_path):
    """Scan fixture media files into an empty database."""
    with Session(db.engine) as session:
        stats = scan_library(session, MEDIA_ROOTS)
        assert stats["movies"] >= 1
        assert stats["episodes"] >= 2

        movies = session.exec(select(Movie)).all()
        shows = session.exec(select(Show)).all()
        episodes = session.exec(select(Episode)).all()

        assert len(movies) >= 1
        assert any("Matrix" in m.title for m in movies)
        assert len(shows) >= 1
        assert any("Breaking Bad" in s.title for s in shows)
        assert len(episodes) >= 2


def test_featurette_files_are_skipped_not_indexed(empty_client, tmp_path):
    """Deleted scenes/featurettes should not become shows or episodes."""
    tv_root = Path(MEDIA_ROOTS[1]["path"])
    featurette = (
        tv_root
        / "Breaking Bad"
        / "Featurettes"
        / "Season 1"
        / "Deleted Scenes"
        / "S01E03 Pilot Deleted Scenes.mkv"
    )
    featurette.parent.mkdir(parents=True, exist_ok=True)
    featurette.touch()

    try:
        with Session(db.engine) as session:
            stats = scan_library(session, MEDIA_ROOTS)
            shows = session.exec(select(Show)).all()
            breaking_bad = next(s for s in shows if s.title == "Breaking Bad")
            fake_shows = [
                s for s in shows if "Deleted Scenes" in s.title and s.id != breaking_bad.id
            ]
            assert fake_shows == []
            assert stats["skipped"] >= 1

            episodes = session.exec(
                select(Episode).where(Episode.show_id == breaking_bad.id)
            ).all()
            assert len(episodes) == 2
            assert not any(ep.title == "Pilot Deleted Scenes" for ep in episodes)
    finally:
        if featurette.exists():
            featurette.unlink()


def test_bracketed_folder_layout_keeps_one_show_per_series(empty_client, tmp_path):
    """Regression: featurettes under [Category]/Show must not flood browse rows."""
    tv_root = Path(MEDIA_ROOTS[1]["path"])
    regular = (
        tv_root
        / "[Sitcoms]"
        / "The Office"
        / "Season 1"
        / "The Office S01E01 Pilot.mkv"
    )
    featurette = (
        tv_root
        / "[Sitcoms]"
        / "The Office"
        / "Featurettes"
        / "Season 1"
        / "Deleted Scenes"
        / "S01E01 Pilot Deleted Scenes.mkv"
    )
    regular.parent.mkdir(parents=True, exist_ok=True)
    featurette.parent.mkdir(parents=True, exist_ok=True)
    regular.touch()
    featurette.touch()

    try:
        with Session(db.engine) as session:
            scan_library(session, MEDIA_ROOTS)
            shows = session.exec(select(Show)).all()
            office_shows = [s for s in shows if s.title == "The Office"]
            assert len(office_shows) == 1
            assert office_shows[0].category == "Sitcoms"
            episodes = session.exec(
                select(Episode).where(Episode.show_id == office_shows[0].id)
            ).all()
            assert len(episodes) == 1
            assert episodes[0].episode == 1
    finally:
        for path in (regular, featurette):
            if path.exists():
                path.unlink()
        for folder in (
            tv_root / "[Sitcoms]" / "The Office",
            tv_root / "[Sitcoms]",
        ):
            if folder.exists():
                for child in sorted(folder.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                for child in sorted(folder.rglob("*"), reverse=True):
                    if child.is_dir():
                        child.rmdir()
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()


def test_is_supplemental_content_detects_featurette_paths():
    path = Path(
        "D:/TV/[Sitcoms]/The Office/Featurettes/Season 1/Deleted Scenes/file.mkv"
    )
    assert is_supplemental_content(path)


def test_parse_episode_coerces_list_season_and_episode():
    parsed = parse_episode(
        Path("01 - Unlocking Disaster (United Airlines Flight 811).mkv"),
        show_title_override="Air Crash Investigation",
    )
    assert parsed is not None
    assert isinstance(parsed["season"], int)
    assert isinstance(parsed["episode"], int)


def test_extract_show_title_from_bracketed_category():
    tv_root = Path("D:/TV")
    path = Path("D:/TV/[Sitcoms]/The Office/Season 1/file.mkv")
    assert extract_show_title_from_path(path, tv_root) == "The Office"


def test_extract_show_title_from_simple_layout():
    tv_root = Path("D:/TV")
    path = Path("D:/TV/Breaking Bad/Season 01/file.mkv")
    assert extract_show_title_from_path(path, tv_root) == "Breaking Bad"


def test_resolve_show_folder_from_bracketed_category():
    tv_root = Path("D:/TV")
    path = Path("D:/TV/[Sitcoms]/The Office/Season 1/file.mkv")
    assert resolve_show_folder_path(path, [tv_root]) == Path("D:/TV/[Sitcoms]/The Office")


def test_resolve_show_folder_from_simple_layout():
    tv_root = Path("D:/TV")
    path = Path("D:/TV/Breaking Bad/Season 01/file.mkv")
    assert resolve_show_folder_path(path, [tv_root]) == Path("D:/TV/Breaking Bad")


def test_resolve_show_folder_falls_back_to_parent_directory():
    path = Path("c:/fixtures/tv/Breaking Bad/S01E01.mkv")
    assert resolve_show_folder_path(path, []) == Path("c:/fixtures/tv/Breaking Bad")


def test_parse_episode_uses_folder_title_for_featurettes():
    parsed = parse_episode(
        Path("S01E03 Pilot Deleted Scenes.mkv"),
        show_title_override="Breaking Bad",
    )
    assert parsed["show_title"] == "Breaking Bad"
    assert parsed["normalized_title"] == "breaking bad"
    assert parsed["episode_title"] == "Pilot Deleted Scenes"


def test_extract_movie_genres_from_sidecar_txt(tmp_path):
    from app.genre_tags import extract_movie_genres

    folder = tmp_path / "17 Again (2009)"
    folder.mkdir()
    video = folder / "17.Again.2009.1080p.BrRip.x264.YIFY.mp4"
    video.touch()
    (folder / "17 Again - Comedy.txt").write_text("", encoding="utf-8")
    assert extract_movie_genres(video) == ["Comedy"]


def test_extract_movie_genres_from_sidecar_with_multiple_genres_and_fav(tmp_path):
    from app.genre_tags import extract_movie_genres

    folder = tmp_path / "1917 (2019)"
    folder.mkdir()
    video = folder / "1917.2019.1080p.WEBRip.x264.AAC5.1-[YTS.MX].mp4"
    video.touch()
    (folder / "1917 (2019) - Drama - War - fav.txt").write_text("", encoding="utf-8")
    assert extract_movie_genres(video) == ["Drama", "War"]


def test_extract_movie_genres_from_sidecar_nfo(tmp_path):
    from app.genre_tags import extract_movie_genres

    folder = tmp_path / "28 Days Later (2002)"
    folder.mkdir()
    video = folder / "28 Days Later (2002) 1080p BrRip 5.1 x264 aac [TuGAZx].mp4"
    video.touch()
    (folder / "28 Days Later - Horror.nfo").write_text("", encoding="utf-8")
    assert extract_movie_genres(video) == ["Horror"]


def test_extract_movie_genres_ignores_torrent_readme_txt(tmp_path):
    from app.genre_tags import extract_movie_genres

    folder = tmp_path / "Some Movie (2020)"
    folder.mkdir()
    video = folder / "Some.Movie.2020.mkv"
    video.touch()
    (folder / "RARBG.txt").write_text("", encoding="utf-8")
    assert extract_movie_genres(video) == []


def test_extract_movie_genres_normalizes_lowercase():
    from app.genre_tags import parse_genres_from_tag_stem

    assert parse_genres_from_tag_stem("8Mile (2002) - drama - biography - music") == [
        "Drama",
        "Biography",
        "Music",
    ]


def test_scan_library_extracts_movie_genres(empty_client, tmp_path):
    from app.genre_tags import parse_genres_json

    movies_root = Path(MEDIA_ROOTS[0]["path"])
    movie_dir = movies_root / "Blade Runner (1982)"
    movie_dir.mkdir(parents=True, exist_ok=True)
    video = movie_dir / "Blade Runner (1982).mkv"
    tag = movie_dir / "Blade Runner (1982) - Sci-Fi.txt"
    video.touch()
    tag.write_text("", encoding="utf-8")

    try:
        with Session(db.engine) as session:
            scan_library(session, MEDIA_ROOTS)
            movies = session.exec(select(Movie)).all()
            blade_runner = next(m for m in movies if "Blade Runner" in m.title)
            assert parse_genres_json(blade_runner.genres) == ["Sci-Fi"]
    finally:
        if tag.exists():
            tag.unlink()
        if video.exists():
            video.unlink()
        if movie_dir.exists() and not any(movie_dir.iterdir()):
            movie_dir.rmdir()


def test_fixture_media_files_exist():
    """Fixture media paths must exist for scanner tests."""
    for root in MEDIA_ROOTS:
        root_path = Path(root["path"])
        assert root_path.exists(), f"Fixture root missing: {root_path}"
        video_files = list(root_path.rglob("*.mkv"))
        assert len(video_files) >= 1, f"No .mkv files under {root_path}"
