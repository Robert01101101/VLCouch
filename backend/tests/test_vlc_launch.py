from unittest.mock import MagicMock, patch

from app.vlc import _http_launch_args, _launch_vlc_process, _subtitle_launch_args, _vlc_launch_env, find_vlc_path


def test_http_launch_args_include_qt_intf():
    args = _http_launch_args(9080, "abc123")
    assert args[0] == "--intf=qt"
    assert "--extraintf=http" in args
    assert "--http-password=abc123" in args


def test_vlc_launch_env_sets_plugin_path(tmp_path):
    (tmp_path / "plugins").mkdir()
    env = _vlc_launch_env(tmp_path)
    assert env["VLC_PLUGIN_PATH"] == str(tmp_path / "plugins")


@patch("app.vlc.settings_store.simple_vlc_playback", return_value=False)
@patch("app.vlc.settings_store.vlc_subtitles_on", return_value=False)
def test_subtitle_launch_args_without_setting(mock_subtitles_on, mock_simple, tmp_path):
    sub = tmp_path / "movie.srt"
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")
    args = _subtitle_launch_args(str(sub))
    assert args == []


@patch("app.vlc.settings_store.simple_vlc_playback", return_value=False)
@patch("app.vlc.settings_store.vlc_subtitles_on", return_value=True)
def test_subtitle_launch_args_with_setting(mock_subtitles_on, mock_simple, tmp_path):
    sub = tmp_path / "movie.srt"
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")
    args = _subtitle_launch_args(str(sub))
    assert args == [f"--sub-file={sub}", "--sub-track=0"]


@patch("app.vlc.settings_store.simple_vlc_playback", return_value=True)
@patch("app.vlc.settings_store.vlc_subtitles_on", return_value=True)
def test_subtitle_launch_args_disabled_in_simple_mode(mock_subtitles_on, mock_simple, tmp_path):
    sub = tmp_path / "movie.srt"
    sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")
    args = _subtitle_launch_args(str(sub))
    assert args == []


@patch("app.vlc.settings_store.simple_vlc_playback", return_value=False)
@patch("app.vlc.settings_store.vlc_subtitles_on", return_value=True)
def test_subtitle_launch_args_embedded_only(mock_subtitles_on, mock_simple):
    args = _subtitle_launch_args(None)
    assert args == ["--sub-track=0"]


@patch("app.vlc.settings_store.vlc_playlist_advance", return_value=True)
def test_playlist_behavior_args_when_enabled(mock_advance):
    from app.vlc import _playlist_behavior_args

    assert _playlist_behavior_args() == ["--no-repeat", "--no-loop"]


@patch("app.vlc.settings_store.vlc_playlist_advance", return_value=False)
def test_playlist_behavior_args_when_disabled(mock_advance):
    from app.vlc import _playlist_behavior_args

    assert _playlist_behavior_args() == []


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


@patch("app.vlc.sys.platform", "linux")
@patch("app.vlc.VLC_PATH", "")
@patch("app.vlc.shutil.which", return_value="/usr/bin/vlc")
def test_find_vlc_path_uses_path_on_linux(mock_which):
    assert find_vlc_path() == "/usr/bin/vlc"
    mock_which.assert_any_call("vlc")
