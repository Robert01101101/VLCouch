from unittest.mock import patch

from sqlmodel import Session, select

import app.db as db
from app.models import PlaybackSession, WatchProgress
from app.playback_service import create_session, finalize_session
from app.watch_service import mark_completed, update_position


def test_create_session_marks_not_watched(client):
    with Session(db.engine) as session:
        playback = create_session(
            session,
            mode="single",
            pid=12345,
            http_port=9080,
            http_password="secret",
            playlist_path=None,
            current_item_type="episode",
            current_item_id=client.seed_data["episode_ids"][1],
        )
        assert playback.status == "active"

        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == client.seed_data["episode_ids"][1],
            )
        ).first()
        assert progress is not None
        assert progress.watched is False
        assert progress.last_position_at is not None


@patch("app.playback_service.fetch_status")
def test_finalize_session_saves_position(mock_status, client):
    from app.vlc_http import VlcStatus

    ep_id = client.seed_data["episode_ids"][1]
    mock_status.return_value = VlcStatus(
        state="playing",
        time=900,
        length=3600,
        position=0.25,
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
        finalize_session(session, playback.id, save_position=True, terminate_vlc=False)

        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress.position_seconds == 900
        assert progress.watched is False

        ended = session.get(PlaybackSession, playback.id)
        assert ended.status == "ended"


@patch("app.playback_service.fetch_status")
def test_finalize_session_marks_complete(mock_status, client):
    from app.vlc_http import VlcStatus

    ep_id = client.seed_data["episode_ids"][1]
    mock_status.return_value = VlcStatus(
        state="playing",
        time=3500,
        length=3600,
        position=0.97,
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
        finalize_session(session, playback.id, save_position=True, terminate_vlc=False)

        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress.watched is True
        assert progress.position_seconds is None


def test_mark_completed_clears_position(client):
    ep_id = client.seed_data["episode_ids"][1]
    with Session(db.engine) as session:
        update_position(session, "episode", ep_id, 900, 3600)
        mark_completed(session, "episode", ep_id)
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress.watched is True
        assert progress.position_seconds is None
