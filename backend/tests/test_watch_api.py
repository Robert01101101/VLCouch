def test_update_watch_status_episode(client):
    ep_id = client.seed_data["episode_ids"][1]
    response = client.post(
        f"/api/watch-status/episode/{ep_id}",
        json={"watched": True},
    )
    assert response.status_code == 200
    assert response.json()["watched"] is True


def test_update_watch_status_movie(client):
    movie_id = client.seed_data["movie_id"]
    response = client.post(
        f"/api/watch-status/movie/{movie_id}",
        json={"watched": True},
    )
    assert response.status_code == 200
    assert response.json()["watched"] is True


def test_watch_status_invalid_type(client):
    response = client.post(
        "/api/watch-status/invalid/1",
        json={"watched": True},
    )
    assert response.status_code == 400


def test_continue_watching(client):
    response = client.get("/api/continue-watching")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["title"] == "Breaking Bad"
    assert items[0]["watched_count"] == 1
    assert items[0]["total_episodes"] == 2
