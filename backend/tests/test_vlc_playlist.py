from app.models import Episode
from app.vlc_playlist import build_m3u, path_to_file_uri


def test_path_to_file_uri_windows():
    uri = path_to_file_uri(r"C:\media\Show\S01E01.mkv")
    assert uri.startswith("file:///C:/media/Show/")
    assert "S01E01.mkv" in uri


def test_build_m3u_subtitles_on_adds_sub_track():
    episodes = [
        Episode(
            id=1,
            show_id=1,
            season=1,
            episode=1,
            title="Pilot",
            file_path=r"C:\media\S01E01.mkv",
        ),
    ]
    content = build_m3u(episodes, subtitles_on=True)
    assert content.count("#EXTVLCOPT:sub-track=0") == 1


def test_build_m3u_plain_playlist_without_extvlcopt():
    episodes = [
        Episode(
            id=1,
            show_id=1,
            season=1,
            episode=1,
            title="Pilot",
            file_path=r"C:\media\S01E01.mkv",
        ),
        Episode(
            id=2,
            show_id=1,
            season=1,
            episode=2,
            title="Second",
            file_path=r"C:\media\S01E02.mkv",
        ),
    ]
    content = build_m3u(episodes)
    assert "#EXTVLCOPT" not in content
    assert "S01E01" in content
    assert "S01E02" in content
    assert content.count("file:///") == 2


def test_build_m3u_resume_start_time_on_first_item_only():
    episodes = [
        Episode(
            id=1,
            show_id=1,
            season=1,
            episode=1,
            title="Pilot",
            file_path=r"C:\media\S01E01.mkv",
        ),
        Episode(
            id=2,
            show_id=1,
            season=1,
            episode=2,
            title="Second",
            file_path=r"C:\media\S01E02.mkv",
        ),
    ]
    content = build_m3u(episodes, start_times={1: 847.2})
    assert content.count("#EXTVLCOPT:start-time=") == 1
    assert "#EXTVLCOPT:start-time=847.2" in content
    assert content.index("#EXTVLCOPT:start-time=847.2") < content.index("S01E02")
