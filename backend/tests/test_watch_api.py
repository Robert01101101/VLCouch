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


def test_update_season_watch_status(client):
    show_id = client.seed_data["show_id"]
    response = client.post(
        f"/api/shows/{show_id}/seasons/1/watch-status",
        json={"watched": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["watched"] is True
    assert data["updated_count"] == 2

    show = client.get(f"/api/shows/{show_id}").json()
    for season in show["seasons"]:
        for ep in season["episodes"]:
            assert ep["watched"] is True

    response = client.post(
        f"/api/shows/{show_id}/seasons/1/watch-status",
        json={"watched": False},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    show = client.get(f"/api/shows/{show_id}").json()
    for season in show["seasons"]:
        for ep in season["episodes"]:
            assert ep["watched"] is False


def test_update_season_watch_status_not_found(client):
    show_id = client.seed_data["show_id"]
    response = client.post(
        f"/api/shows/{show_id}/seasons/99/watch-status",
        json={"watched": True},
    )
    assert response.status_code == 404

    response = client.post(
        "/api/shows/99999/seasons/1/watch-status",
        json={"watched": True},
    )
    assert response.status_code == 404
