import importlib


def test_vlcouch_data_dir_override(monkeypatch, tmp_path):
    data_dir = tmp_path / "installed-data"
    monkeypatch.setenv("VLCOUCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("TEST_DB_PATH", raising=False)
    monkeypatch.delenv("TEST_POSTERS_DIR", raising=False)

    import app.config as config

    importlib.reload(config)

    try:
        assert config.DATA_DIR == data_dir
        assert config.DB_PATH == data_dir / "library.db"
        assert config.POSTERS_DIR == data_dir / "posters"
        assert config.PLAYLISTS_DIR == data_dir / "playlists"
    finally:
        monkeypatch.delenv("VLCOUCH_DATA_DIR", raising=False)
        monkeypatch.setenv("APP_ENV", "test")
        importlib.reload(config)
