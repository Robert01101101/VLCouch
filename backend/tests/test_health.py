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
