from app.vlc_http import VlcStatus, _parse_status_filename, is_playback_complete


def test_parse_status_filename_vlc3_list_format():
    data = {
        "information": {
            "category": [
                {
                    "name": "meta",
                    "info": [{"name": "filename", "$": "Show S01E01.mkv"}],
                }
            ]
        }
    }
    assert _parse_status_filename(data) == "Show S01E01.mkv"


def test_parse_status_filename_vlc4_dict_format():
    data = {
        "information": {
            "category": {
                "Stream 0": {"Type": "Video"},
                "meta": {"filename": "Show S01E01.mkv", "title": "Pilot"},
            }
        }
    }
    assert _parse_status_filename(data) == "Show S01E01.mkv"


def test_is_playback_complete_by_ratio():
    status = VlcStatus(
        state="playing",
        time=2700,
        length=3000,
        position=0.91,
        currentplid=1,
        filename="test.mkv",
    )
    assert is_playback_complete(status) is True


def test_is_playback_complete_by_end_seconds():
    status = VlcStatus(
        state="playing",
        time=2975,
        length=3000,
        position=0.85,
        currentplid=1,
        filename="test.mkv",
    )
    assert is_playback_complete(status) is True


def test_is_playback_complete_mid_episode():
    status = VlcStatus(
        state="playing",
        time=600,
        length=3000,
        position=0.2,
        currentplid=1,
        filename="test.mkv",
    )
    assert is_playback_complete(status) is False
