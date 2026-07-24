from sqlmodel import Session

import app.db as db
import app.settings_store as settings_store


def test_get_media_roots_seeded_from_env(empty_client):
    response = empty_client.get("/api/media-roots")
    assert response.status_code == 200
    roots = response.json()["roots"]
    assert len(roots) >= 2
    types = {root["type"] for root in roots}
    assert "movies" in types
    assert "tv" in types


def test_put_media_roots_persists(empty_client):
    payload = {
        "roots": [
            {"path": "D:/Movies", "type": "movies"},
            {"path": "E:/TV Shows", "type": "tv"},
        ]
    }
    response = empty_client.put("/api/media-roots", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["roots"] == payload["roots"]

    response = empty_client.get("/api/media-roots")
    assert response.json()["roots"] == payload["roots"]


def test_put_media_roots_deduplicates_and_validates(empty_client):
    payload = {
        "roots": [
            {"path": "D:/Movies", "type": "movies"},
            {"path": " d:/movies ", "type": "movies"},
            {"path": "", "type": "movies"},
            {"path": "D:/TV", "type": "shows"},
        ]
    }
    response = empty_client.put("/api/media-roots", json=payload)
    assert response.status_code == 422

    valid = empty_client.put(
        "/api/media-roots",
        json={
            "roots": [
                {"path": "D:/Movies", "type": "movies"},
                {"path": " d:/movies ", "type": "movies"},
                {"path": "D:/TV", "type": "tv"},
            ]
        },
    )
    assert valid.status_code == 200
    assert valid.json()["roots"] == [
        {"path": "D:/Movies", "type": "movies"},
        {"path": "D:/TV", "type": "tv"},
    ]


def test_pick_folder_unavailable_in_test_mode(empty_client):
    response = empty_client.post("/api/media-roots/pick-folder")
    assert response.status_code == 503


def test_media_roots_used_by_scan(empty_client, tmp_path):
    movies_dir = tmp_path / "movies"
    tv_dir = tmp_path / "tv"
    movies_dir.mkdir()
    tv_dir.mkdir()
    (movies_dir / "Sample Movie (2020).mkv").write_bytes(b"x")

    empty_client.put(
        "/api/media-roots",
        json={
            "roots": [
                {"path": str(movies_dir), "type": "movies"},
                {"path": str(tv_dir), "type": "tv"},
            ]
        },
    )

    with Session(db.engine):
        assert settings_store.media_roots()[0]["path"] == str(movies_dir)

    response = empty_client.post("/api/scan")
    assert response.status_code == 200
    assert response.json()["status"] == "scan_started"
