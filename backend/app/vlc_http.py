"""VLC HTTP remote control helpers."""

from __future__ import annotations

import ctypes
import logging
import socket
from dataclasses import dataclass

import httpx

from app.config import (
    PLAYBACK_COMPLETION_RATIO,
    PLAYBACK_END_SECONDS,
    VLC_HTTP_PORT_BASE,
    VLC_HTTP_PORT_MAX,
)

logger = logging.getLogger(__name__)

STILL_ACTIVE = 259


@dataclass
class VlcStatus:
    state: str
    time: float
    length: float
    position: float
    currentplid: int | None
    filename: str | None


def allocate_http_port() -> int:
    """Return the first port in range that can be bound on localhost."""
    for port in range(VLC_HTTP_PORT_BASE, VLC_HTTP_PORT_MAX + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"No free VLC HTTP port in range {VLC_HTTP_PORT_BASE}-{VLC_HTTP_PORT_MAX}"
    )


def is_pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def terminate_pid(pid: int | None) -> None:
    if not pid or not is_pid_alive(pid):
        return
    handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
    if handle:
        ctypes.windll.kernel32.TerminateProcess(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)


def _parse_status_filename(data: dict) -> str | None:
    """Extract filename from status.json (VLC 3 list format or VLC 4 dict format)."""
    info = data.get("information") or {}
    category = info.get("category")
    if isinstance(category, dict):
        meta = category.get("meta")
        if isinstance(meta, dict):
            filename = meta.get("filename")
            if isinstance(filename, str) and filename:
                return filename
        return None

    if isinstance(category, list):
        for cat in category:
            if not isinstance(cat, dict) or cat.get("name") != "meta":
                continue
            for item in cat.get("info") or []:
                if isinstance(item, dict) and item.get("name") == "filename":
                    value = item.get("$")
                    if isinstance(value, str) and value:
                        return value
    return None


def fetch_status(port: int, password: str) -> VlcStatus | None:
    url = f"http://127.0.0.1:{port}/requests/status.json"
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url, auth=("", password))
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("VLC status fetch failed on port %s: %s", port, exc)
        return None

    filename = None
    try:
        filename = _parse_status_filename(data)
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug("VLC status filename parse failed on port %s: %s", port, exc)

    currentplid = data.get("currentplid")
    return VlcStatus(
        state=str(data.get("state") or "stopped"),
        time=float(data.get("time") or 0),
        length=float(data.get("length") or 0),
        position=float(data.get("position") or 0),
        currentplid=int(currentplid) if currentplid is not None else None,
        filename=filename,
    )


def fetch_playlist_map(port: int, password: str) -> dict[int, str]:
    """Map playlist item id to media URI."""
    url = f"http://127.0.0.1:{port}/requests/playlist.json"
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url, auth=("", password))
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return {}

    result: dict[int, str] = {}

    def walk(node: dict) -> None:
        node_id = node.get("id")
        if node_id is not None and node.get("uri"):
            result[int(node_id)] = str(node["uri"])
        for child in node.get("children") or []:
            walk(child)

    for child in data.get("children") or []:
        walk(child)
    return result


def is_playback_complete(status: VlcStatus) -> bool:
    if status.length <= 0:
        return False
    if status.position >= PLAYBACK_COMPLETION_RATIO:
        return True
    return (status.length - status.time) <= PLAYBACK_END_SECONDS
