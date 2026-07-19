def test_browse_returns_rows(client):
    response = client.get("/api/browse")
    assert response.status_code == 200
    data = response.json()
    assert "hero" in data
    assert "rows" in data
    assert isinstance(data["rows"], list)
    assert len(data["rows"]) > 0


def test_browse_row_shape(client):
    response = client.get("/api/browse")
    rows = response.json()["rows"]
    for row in rows:
        assert "id" in row
        assert "title" in row
        assert "item_type" in row
        assert "items" in row
        assert isinstance(row["items"], list)


def test_browse_has_movie_decade_row(client):
    response = client.get("/api/browse")
    rows = response.json()["rows"]
    movie_rows = [r for r in rows if r["item_type"] == "movie"]
    assert len(movie_rows) >= 1
    assert any("Matrix" in item["title"] for row in movie_rows for item in row["items"])


def test_browse_has_top_genre_rows(client):
    response = client.get("/api/browse")
    rows = response.json()["rows"]
    genre_rows = [row for row in rows if row["id"].startswith("genre-")]
    assert len(genre_rows) >= 1
    assert len(genre_rows) <= 5
    sci_fi = next(row for row in genre_rows if row["id"] == "genre-sci-fi")
    assert sci_fi["title"] == "Sci-Fi Movies"
    assert sci_fi["item_type"] == "movie"
    assert any(item["title"] == "The Matrix" for item in sci_fi["items"])
    action = next(row for row in genre_rows if row["id"] == "genre-action")
    assert any(item["title"] == "The Matrix" for item in action["items"])


def test_order_row_items_alphabetical_by_default():
    from unittest.mock import patch

    from app.routers.library import _order_row_items

    items = [{"id": 1, "title": "Zulu"}, {"id": 2, "title": "Alpha"}]
    with patch("app.routers.library.settings_store.browse_row_random", return_value=False):
        ordered = _order_row_items(items)
    assert [item["title"] for item in ordered] == ["Alpha", "Zulu"]


def test_order_row_items_random_when_enabled():
    from unittest.mock import patch

    from app.routers.library import _order_row_items

    items = [
        {"id": 1, "title": "Alpha"},
        {"id": 2, "title": "Mike"},
        {"id": 3, "title": "Zulu"},
    ]
    with patch("app.routers.library.settings_store.browse_row_random", return_value=True):
        first = _order_row_items(items, browse_session="session-a", row_id="movies-1990s")
        second = _order_row_items(items, browse_session="session-a", row_id="movies-1990s")
        third = _order_row_items(items, browse_session="session-b", row_id="movies-1990s")
    assert first == second
    assert [item["title"] for item in first] != ["Alpha", "Mike", "Zulu"]
    assert third != first or len(items) <= 1


def test_browse_excludes_continue_watching_row(client):
    movie_id = client.seed_data["movie_id"]
    client.post(f"/api/watch-status/movie/{movie_id}", json={"watched": True})
    response = client.get("/api/browse")
    rows = response.json()["rows"]
    row_ids = {row["id"] for row in rows}
    assert "continue-watching" not in row_ids


def test_browse_has_recently_watched_as_first_row(client):
    response = client.get("/api/browse")
    rows = response.json()["rows"]
    assert len(rows) > 0
    assert rows[0]["id"] == "recently-watched"
    assert rows[0]["title"] == "Recently Watched"
    assert rows[0]["item_type"] == "mixed"
    assert any(item["title"] == "Breaking Bad" for item in rows[0]["items"])


def test_browse_no_recently_watched_row_when_empty(empty_client):
    response = empty_client.get("/api/browse")
    row_ids = {row["id"] for row in response.json()["rows"]}
    assert "recently-watched" not in row_ids


def test_browse_promotes_played_rows_after_recently_watched(client):
    """Rows with play history float up; Recently Watched stays first."""
    rows_before = client.get("/api/browse").json()["rows"]
    row_ids_before = [row["id"] for row in rows_before]
    assert row_ids_before[0] == "recently-watched"

    movie_id = client.seed_data["movie_id"]
    client.post(f"/api/watch-status/movie/{movie_id}", json={"watched": True})

    rows = client.get("/api/browse").json()["rows"]
    row_ids = [row["id"] for row in rows]
    assert row_ids[0] == "recently-watched"

    movie_row_ids = {
        row_id
        for row_id in row_ids
        if row_id == "movies-1990s" or row_id.startswith("genre-")
    }
    assert movie_row_ids
    first_movie_row_idx = min(row_ids.index(row_id) for row_id in movie_row_ids)
    drama_idx = row_ids.index("tv-drama")
    assert first_movie_row_idx < drama_idx


def test_browse_hero_includes_overview_for_episode(client):
    response = client.get("/api/browse")
    hero = response.json()["hero"]
    assert hero is not None
    assert "overview" in hero


def test_list_movies(client):
    response = client.get("/api/movies")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["title"] == "The Matrix"
    assert movies[0]["year"] == 1999


def test_list_shows(client):
    response = client.get("/api/shows")
    assert response.status_code == 200
    shows = response.json()
    assert len(shows) == 1
    assert shows[0]["title"] == "Breaking Bad"
    assert shows[0]["episode_count"] == 2


def test_get_show_detail(client):
    show_id = client.seed_data["show_id"]
    response = client.get(f"/api/shows/{show_id}")
    assert response.status_code == 200
    show = response.json()
    assert show["title"] == "Breaking Bad"
    assert len(show["seasons"]) == 1
    assert len(show["seasons"][0]["episodes"]) == 2


def test_get_show_not_found(client):
    response = client.get("/api/shows/9999")
    assert response.status_code == 404


def test_search_requires_min_length(client):
    response = client.get("/api/search", params={"q": "a"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_finds_movies_and_shows(client):
    response = client.get("/api/search", params={"q": "matrix"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert any(r["title"] == "The Matrix" and r["item_type"] == "movie" for r in results)

    response = client.get("/api/search", params={"q": "breaking"})
    results = response.json()["results"]
    assert any(r["title"] == "Breaking Bad" and r["item_type"] == "show" for r in results)


def test_search_is_case_insensitive(client):
    response = client.get("/api/search", params={"q": "BREAKING"})
    results = response.json()["results"]
    assert any(r["title"] == "Breaking Bad" for r in results)


def test_browse_returns_hero_when_watch_progress_exists(client):
    ep_id = client.seed_data["episode_ids"][1]
    response = client.get("/api/browse")
    assert response.status_code == 200
    hero = response.json()["hero"]
    assert hero is not None
    assert hero["item_type"] == "episode"
    assert hero["episode_id"] == ep_id
    assert hero["show_title"] == "Breaking Bad"
    assert hero["last_watched_at"] is not None


def test_browse_hero_is_episode_level_for_tv(client):
    ep_id = client.seed_data["episode_ids"][1]
    response = client.get("/api/browse")
    hero = response.json()["hero"]
    assert hero["item_type"] == "episode"
    assert hero["episode_id"] == ep_id
    assert hero["season"] == 1
    assert hero["episode"] == 2
    assert hero["episode_title"] == "Cat's in the Bag..."
    assert hero["show_id"] == client.seed_data["show_id"]
    assert "poster_url" in hero
    assert "thumbnail_url" in hero


def test_browse_hero_null_when_nothing_watched(empty_client):
    response = empty_client.get("/api/browse")
    assert response.status_code == 200
    assert response.json()["hero"] is None


def test_browse_hero_movie_when_movie_watched_last(client):
    movie_id = client.seed_data["movie_id"]
    client.post(f"/api/watch-status/movie/{movie_id}", json={"watched": True})
    response = client.get("/api/browse")
    hero = response.json()["hero"]
    assert hero is not None
    assert hero["item_type"] == "movie"
    assert hero["id"] == movie_id
    assert hero["title"] == "The Matrix"
    assert "thumbnail_url" in hero


def test_browse_hero_ignores_null_last_watched_at(client):
    """Rows with null last_watched_at must not shadow real watch history."""
    from sqlmodel import Session

    import app.db as db
    from app.models import WatchProgress

    movie_id = client.seed_data["movie_id"]
    with Session(db.engine) as session:
        session.add(
            WatchProgress(
                item_type="movie",
                item_id=movie_id,
                watched=True,
                last_watched_at=None,
            )
        )
        session.commit()

    hero = client.get("/api/browse").json()["hero"]
    assert hero is not None
    assert hero["item_type"] == "episode"
    assert hero["episode_id"] == client.seed_data["episode_ids"][1]


def test_play_marks_watched(client):
    ep_id = client.seed_data["episode_ids"][1]
    client.post(f"/api/watch-status/episode/{ep_id}", json={"watched": True})
    browse = client.get("/api/browse").json()
    assert browse["hero"] is None


def test_browse_hero_in_progress(client):
    ep_id = client.seed_data["episode_ids"][1]
    from sqlmodel import Session

    import app.db as db
    from app.watch_service import update_position

    with Session(db.engine) as session:
        update_position(session, "episode", ep_id, 600, 3600)

    hero = client.get("/api/browse").json()["hero"]
    assert hero is not None
    assert hero["episode_id"] == ep_id
    assert hero.get("in_progress") is True
    assert hero.get("resume_from_seconds") == 600


def test_browse_hero_updates_when_episode_marked_watched(client):
    ep2_id = client.seed_data["episode_ids"][1]
    assert client.get("/api/browse").json()["hero"]["episode_id"] == ep2_id

    client.post(f"/api/watch-status/episode/{ep2_id}", json={"watched": True})
    assert client.get("/api/browse").json()["hero"] is None


def test_browse_hero_uses_episode_after_last_watched_not_first_gap(client):
    from sqlmodel import Session

    import app.db as db
    from app.models import Episode

    show_id = client.seed_data["show_id"]
    with Session(db.engine) as session:
        ep3 = Episode(
            show_id=show_id,
            season=1,
            episode=3,
            title="...And the Bag's in the River",
            file_path="c:/fixtures/tv/Breaking Bad/S01E03.mkv",
        )
        ep4 = Episode(
            show_id=show_id,
            season=1,
            episode=4,
            title="Cancer Man",
            file_path="c:/fixtures/tv/Breaking Bad/S01E04.mkv",
        )
        session.add(ep3)
        session.add(ep4)
        session.commit()
        ep3_id = ep3.id
        ep4_id = ep4.id

    client.post(f"/api/watch-status/episode/{ep3_id}", json={"watched": True})
    hero = client.get("/api/browse").json()["hero"]
    assert hero is not None
    assert hero["episode_id"] == ep4_id
    assert hero["episode"] == 4


def test_get_show_queues_episode_thumbnails_when_auto_enabled(client):
    from unittest.mock import ANY, patch

    client.patch("/api/settings", json={"auto_generate_thumbnails": True})
    show_id = client.seed_data["show_id"]

    with patch("app.routers.library.queue_show_episode_thumbnails") as mock_queue:
        response = client.get(f"/api/shows/{show_id}")
        assert response.status_code == 200
        mock_queue.assert_called_once_with(show_id, ANY)


def test_get_show_skips_episode_thumbnails_when_auto_disabled(client):
    from unittest.mock import patch

    client.patch("/api/settings", json={"auto_generate_thumbnails": False})
    show_id = client.seed_data["show_id"]

    with patch("app.routers.library.queue_show_episode_thumbnails") as mock_queue:
        response = client.get(f"/api/shows/{show_id}")
        assert response.status_code == 200
        mock_queue.assert_not_called()
