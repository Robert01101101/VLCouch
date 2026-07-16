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
