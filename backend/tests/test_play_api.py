def test_play_movie(client):
    movie_id = client.seed_data["movie_id"]
    response = client.post(f"/api/play/movie/{movie_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["item_type"] == "movie"
    assert data["title"] == "The Matrix"


def test_play_episode(client):
    ep_id = client.seed_data["episode_ids"][0]
    response = client.post(f"/api/play/episode/{ep_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["item_type"] == "episode"

    import app.db as db
    from sqlmodel import Session, select
    from app.models import WatchProgress

    with Session(db.engine) as session:
        progress = session.exec(
            select(WatchProgress).where(
                WatchProgress.item_type == "episode",
                WatchProgress.item_id == ep_id,
            )
        ).first()
        assert progress is not None
        assert progress.watched is True
        assert progress.last_watched_at is not None


def test_play_invalid_type(client):
    response = client.post("/api/play/invalid/1")
    assert response.status_code == 400


def test_play_not_found(client):
    response = client.post("/api/play/movie/9999")
    assert response.status_code == 404
