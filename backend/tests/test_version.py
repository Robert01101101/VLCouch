from pathlib import Path

from app.version import load_app_version


def test_load_app_version_reads_repo_root_version():
    root_version = Path(__file__).resolve().parents[2] / "VERSION"
    expected = root_version.read_text(encoding="utf-8").strip()
    assert load_app_version() == expected
