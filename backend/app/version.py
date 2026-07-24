from pathlib import Path

_DEFAULT_VERSION = "0.1.0"


def load_app_version() -> str:
    """Read version from packaged version.txt or repo-root VERSION."""
    app_dir = Path(__file__).resolve().parent
    for candidate in (app_dir / "version.txt", app_dir.parent.parent / "VERSION"):
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    return _DEFAULT_VERSION
