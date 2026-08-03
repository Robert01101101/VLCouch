from unittest.mock import patch


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "vlc_launch_profile" in data


def test_scan_status_not_running_by_default(client):
    response = client.get("/api/scan/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False


def test_thumbnail_status_idle_by_default(client):
    response = client.get("/api/thumbnails/status")
    assert response.status_code == 200
    data = response.json()
    assert data["busy"] is False
    assert data["queue_size"] == 0
    assert data["in_flight"] == 0


def test_thumbnail_status_reports_busy_when_in_flight(client):
    from app.thumbnail_worker import _in_flight

    _in_flight.add("movie:1")
    try:
        response = client.get("/api/thumbnails/status")
        assert response.status_code == 200
        data = response.json()
        assert data["busy"] is True
        assert data["in_flight"] == 1
    finally:
        _in_flight.discard("movie:1")


def test_trigger_scan_defaults_to_quick_mode(client):
    with patch("app.main.scan_state.start_background_scan", return_value=True) as mock_start:
        response = client.post("/api/scan")
        assert response.status_code == 200
        assert response.json() == {"status": "scan_started", "mode": "quick"}
        assert mock_start.call_args.kwargs.get("mode") == "quick"


def test_trigger_scan_full_mode(client):
    with patch("app.main.scan_state.start_background_scan", return_value=True) as mock_start:
        response = client.post("/api/scan?mode=full")
        assert response.status_code == 200
        assert response.json() == {"status": "scan_started", "mode": "full"}
        assert mock_start.call_args.kwargs.get("mode") == "full"


def test_trigger_scan_rejects_invalid_mode(client):
    response = client.post("/api/scan?mode=bogus")
    assert response.status_code == 422


def test_trigger_scan_already_running(client):
    with patch("app.main.scan_state.start_background_scan", return_value=False):
        response = client.post("/api/scan")
        assert response.status_code == 200
        assert response.json() == {"status": "scan_already_running"}


def test_scan_status_reports_stats_counters_after_scan(empty_client):
    from app import scan_state

    scan_state.run_scan(mode="quick")
    response = empty_client.get("/api/scan/status")
    assert response.status_code == 200
    stats = response.json()["last_stats"]
    assert stats["mode"] == "quick"
    for key in ("removed", "renamed", "skipped_unchanged"):
        assert key in stats


def test_start_background_scan_marks_running_before_task():
    from unittest.mock import MagicMock

    from app import scan_state

    original_running = scan_state._state["running"]
    try:
        scan_state._state["running"] = False
        tasks = MagicMock()

        started = scan_state.start_background_scan(tasks, mode="quick")

        assert started is True
        assert scan_state.is_scanning() is True
        tasks.add_task.assert_called_once_with(scan_state.run_scan, "quick")
    finally:
        scan_state._state["running"] = original_running
