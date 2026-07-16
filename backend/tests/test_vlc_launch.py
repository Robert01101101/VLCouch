from pathlib import Path
from unittest.mock import MagicMock, patch

from app.vlc import _http_launch_args, _launch_vlc_process, _vlc_launch_env


def test_http_launch_args_include_qt_intf():
    args = _http_launch_args(9080, "abc123")
    assert args[0] == "--intf=qt"
    assert "--extraintf=http" in args
    assert "--http-password=abc123" in args


def test_vlc_launch_env_sets_plugin_path(tmp_path):
    (tmp_path / "plugins").mkdir()
    env = _vlc_launch_env(tmp_path)
    assert env["VLC_PLUGIN_PATH"] == str(tmp_path / "plugins")


@patch("app.vlc.TEST_MODE", False)
@patch("app.vlc.subprocess.Popen")
@patch("app.vlc._vlc_launch_env", return_value={"VLC_PLUGIN_PATH": "C:\\VLC\\plugins"})
@patch("app.vlc.find_vlc_path", return_value=r"C:\VLC\vlc.exe")
def test_launch_vlc_process_uses_install_dir_cwd(mock_find, mock_env, mock_popen):
    mock_popen.return_value = MagicMock(pid=4242)
    pid = _launch_vlc_process(["--play-and-exit", "movie.mkv"])
    assert pid == 4242
    kwargs = mock_popen.call_args.kwargs
    assert kwargs["cwd"] == r"C:\VLC"
    assert kwargs["env"]["VLC_PLUGIN_PATH"] == r"C:\VLC\plugins"
