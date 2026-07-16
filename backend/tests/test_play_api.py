from sqlmodel import Session, select

import app.db as db
from app.models import PlaybackSession, WatchProgress


def test_play_movie(client):
    movie_id = client.seed_data["movie_id"]
    response = client.post(f"/api/play/movie/{movie_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["item_type"] == "movie"
    assert data["title"] == "The Matrix"
    assert data["mode"] == "single"
    assert data["watched"] is False
    assert "session_id" in data


def test_play_episode(client):
    ep_id = client.seed_data["episode_ids"][1]
    response = client.post(f"/api/play/episode/{ep_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["item_type"] == "episode"
    assert data["mode"] == "playlist"
    assert data["watched"] is False
    assert data["playlist_count"] >= 1

    with Session(db.engine) as session:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress is not None
        assert progress.watched is False
        assert progress.last_position_at is not None

        playback = session.exec(select(PlaybackSession)).first()
        assert playback is not None
        assert playback.status == "active"


def test_play_simple_vlc_mode(client):
    client.patch("/api/settings", json={"simple_vlc_playback": True})
    ep_id = client.seed_data["episode_ids"][1]
    response = client.post(f"/api/play/episode/{ep_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "simple"
    assert data["session_id"] is None
    assert data["playlist_count"] == 1

    with Session(db.engine) as session:
        playback = session.exec(select(PlaybackSession)).first()
        assert playback is None


def test_play_invalid_type(client):
    response = client.post("/api/play/invalid/1")
    assert response.status_code == 400


def test_play_not_found(client):
    response = client.post("/api/play/movie/9999")
    assert response.status_code == 404


def test_playback_session_endpoint(client):
    ep_id = client.seed_data["episode_ids"][1]
    client.post(f"/api/play/episode/{ep_id}")
    response = client.get("/api/playback/session")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["current_item_id"] == ep_id
