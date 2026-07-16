from unittest.mock import patch

import pytest

from app.thumbnail_worker import _in_flight, enqueue


@pytest.fixture(autouse=True)
def reset_thumbnail_worker_state():
    _in_flight.clear()
    yield
    _in_flight.clear()


def test_enqueue_deduplicates_same_job(monkeypatch):
    monkeypatch.setattr("app.thumbnail_worker.TEST_MODE", False)
    monkeypatch.setattr("app.thumbnail_worker._ensure_worker", lambda: None)

    assert enqueue("show_episodes", 26) is True
    assert enqueue("show_episodes", 26) is False


def test_enqueue_allows_different_shows(monkeypatch):
    monkeypatch.setattr("app.thumbnail_worker.TEST_MODE", False)
    monkeypatch.setattr("app.thumbnail_worker._ensure_worker", lambda: None)

    assert enqueue("show_episodes", 26) is True
    assert enqueue("show_episodes", 27) is True


def test_season_watch_queues_one_show_job(client):
    show_id = client.seed_data["show_id"]

    with patch("app.routers.watch.queue_show_episode_thumbnails") as mock_queue:
        response = client.post(
            f"/api/shows/{show_id}/seasons/1/watch-status",
            json={"watched": True},
        )
        assert response.status_code == 200
        mock_queue.assert_called_once()
        assert mock_queue.call_args[0][0] == show_id
