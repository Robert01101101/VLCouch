from unittest.mock import patch

from sqlmodel import Session, select

import app.db as db
from app.models import PlaybackSession, PlaybackSessionItem, WatchProgress
from app.playback_poller import tick_once
from app.playback_service import create_session


@patch("app.playback_service.fetch_status")
def test_poll_session_updates_position(mock_status, client):
    from app.vlc_http import VlcStatus

    ep_id = client.seed_data["episode_ids"][1]
    mock_status.return_value = VlcStatus(
        state="playing",
        time=500,
        length=3600,
        position=0.14,
        currentplid=1,
        filename="test.mkv",
    )

    with Session(db.engine) as session:
        playback = create_session(
            session,
            mode="single",
            pid=12345,
            http_port=9080,
            http_password="secret",
            playlist_path=None,
            current_item_type="episode",
            current_item_id=ep_id,
        )
        session_id = playback.id

    tick_once(session_id)

    with Session(db.engine) as session:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress.position_seconds == 500


@patch("app.playback_service.fetch_playlist_map")
@patch("app.playback_service.fetch_status")
def test_poll_session_detects_plid_change(mock_status, mock_playlist, client):
    from app.vlc_http import VlcStatus

    ep1 = client.seed_data["episode_ids"][0]
    ep2 = client.seed_data["episode_ids"][1]

    mock_playlist.return_value = {2: "file:///C:/media/S01E02.mkv"}

    with Session(db.engine) as session:
        playback = create_session(
            session,
            mode="playlist",
            pid=12345,
            http_port=9080,
            http_password="secret",
            playlist_path=None,
            current_item_type="episode",
            current_item_id=ep1,
            playlist_items=[
                ("episode", ep1, r"C:\media\S01E01.mkv"),
                ("episode", ep2, r"C:\media\S01E02.mkv"),
            ],
        )
        playback.current_plid = 1
        playback.last_poll_time = 3500
        playback.last_poll_length = 3600
        playback.last_poll_position = 0.97
        session.add(playback)
        session.commit()
        session_id = playback.id

    mock_status.return_value = VlcStatus(
        state="playing",
        time=100,
        length=3600,
        position=0.03,
        currentplid=2,
        filename="S01E02.mkv",
    )
    tick_once(session_id)

    with Session(db.engine) as session:
        playback = session.get(PlaybackSession, session_id)
        assert playback.current_item_id == ep2

        items = session.exec(
            select(PlaybackSessionItem).where(
                PlaybackSessionItem.session_id == session_id
            )
        ).all()
        plids = {item.item_id: item.plid for item in items}
        assert plids.get(ep2) == 2
