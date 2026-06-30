# 34 passed
from unittest.mock import patch, MagicMock
from breaker.ui.timer import ask_duration, pomodoro_timer


@patch("rich.prompt.IntPrompt.ask", return_value=5)
def test_ask_duration_valid(mock_input):
    # Проверяем, что ask_duration возвращает корректное значение.
    result = ask_duration()
    assert result == 5


@patch("rich.prompt.IntPrompt.ask", return_value=1)
def test_ask_duration_minimum(mock_input):
    # Минимальное значение — 1 минута.
    result = ask_duration()
    assert result == 1


@patch("rich.prompt.IntPrompt.ask", return_value=50)
def test_ask_duration_maximum(mock_input):
    # Максимальное значение — 50 минут.
    result = ask_duration()
    assert result == 50


@patch("breaker.ui.timer.time.sleep")
def test_pomodoro_timer_completes(mock_sleep):
    # Таймер должен завершиться без ошибок (0 минут = мгновенное завершение).
    result = pomodoro_timer(minutes=0)
    assert result is True


@patch("rich.prompt.IntPrompt.ask", return_value=10)
@patch("breaker.ui.timer.time.sleep")
def test_run_timer_with_prompt(mock_sleep, mock_input):
    # Полный цикл: спросить минуты -> запустить таймер.
    from breaker.ui.timer import run_timer_with_prompt

    result = run_timer_with_prompt()
    assert result is True


def test_format_seconds():
    """_format_seconds() - форматирование секунд."""
    from breaker.ui.timer import _format_seconds
    assert _format_seconds(0) == "00:00"
    assert _format_seconds(59) == "00:59"
    assert _format_seconds(60) == "01:00"
    assert _format_seconds(3661) == "61:01"


@patch("breaker.ui.timer._is_wsl", return_value=False)
@patch("breaker.ui.timer.sys.platform", "darwin")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_macos(mock_run, mock_is_wsl, capsys):
    """_play_sound() на macOS - используется afplay."""
    from breaker.ui.timer import _play_sound
    with patch("pathlib.Path.exists", return_value=True):
        _play_sound()
    if mock_run.called:
        call_args = mock_run.call_args
        assert call_args.args[0][0] == "afplay"

@patch("breaker.ui.timer._is_wsl", return_value=False)
@patch("breaker.ui.timer.sys.platform", "linux")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_linux(mock_run, mock_is_wsl, capsys):
    """_play_sound() на Linux - перебирает плееры."""
    from breaker.ui.timer import _play_sound
    with patch("pathlib.Path.exists", return_value=True):
        mock_run.return_value = MagicMock(returncode=0)
        _play_sound()
    if mock_run.called:
        call_args = mock_run.call_args
        assert call_args.args[0][0] in ["paplay", "mpv", "ffplay", "aplay"]


def test_ask_duration_invalid_then_valid():
    """ask_duration() - невалидный ввод, потом валидный."""
    from breaker.ui.timer import ask_duration
    with patch("rich.prompt.IntPrompt.ask", side_effect=[ValueError(), 5]):
        result = ask_duration()
    assert result == 5


@patch("rich.prompt.IntPrompt.ask", return_value=0)
def test_ask_duration_minimum_boundary(mock_input):
    """ask_duration() - граница минимума."""
    from breaker.ui.timer import ask_duration
    with patch("rich.prompt.IntPrompt.ask", side_effect=[0, 1]):
        result = ask_duration()
    assert result == 1


@patch("rich.prompt.IntPrompt.ask", return_value=51)
def test_ask_duration_maximum_boundary(mock_input):
    """ask_duration() - граница максимума."""
    from breaker.ui.timer import ask_duration
    with patch("rich.prompt.IntPrompt.ask", side_effect=[51, 50]):
        result = ask_duration()
    assert result == 50


@patch("breaker.ui.timer.time.sleep")
@patch("rich.prompt.IntPrompt.ask", return_value=0)
def test_pomodoro_timer_zero_minutes(mock_input, mock_sleep, capsys):
    """pomodoro_timer() - 0 минут (граничный случай)."""
    from breaker.ui.timer import pomodoro_timer
    result = pomodoro_timer(minutes=0)
    assert result is True

def test_format_seconds_zero():
    """_format_seconds() — 0 секунд."""
    from breaker.ui.timer import _format_seconds
    assert _format_seconds(0) == "00:00"


def test_format_seconds_minutes_only():
    """_format_seconds() — только минуты."""
    from breaker.ui.timer import _format_seconds
    assert _format_seconds(300) == "05:00"
    assert _format_seconds(60) == "01:00"


def test_format_seconds_with_seconds():
    """_format_seconds() — минуты и секунды."""
    from breaker.ui.timer import _format_seconds
    assert _format_seconds(65) == "01:05"
    assert _format_seconds(90) == "01:30"
    assert _format_seconds(3661) == "61:01"


def test_is_wsl_false_on_macos():
    """_is_wsl() — возвращает False на macOS (не WSL)."""
    from breaker.ui.timer import _is_wsl
    import os
    # Очищаем переменную окружения WSL
    old_wsl = os.environ.pop("WSL_DISTRO_NAME", None)
    try:
        # Мокнем /proc/version, чтобы он не содержал "microsoft"
        with patch("builtins.open", side_effect=OSError("No such file")):
            result = _is_wsl()
        assert result is False
    finally:
        if old_wsl is not None:
            os.environ["WSL_DISTRO_NAME"] = old_wsl


def test_is_wsl_true_with_env_var():
    """_is_wsl() — возвращает True при наличии WSL_DISTRO_NAME."""
    from breaker.ui.timer import _is_wsl
    import os
    old_wsl = os.environ.get("WSL_DISTRO_NAME")
    try:
        os.environ["WSL_DISTRO_NAME"] = "Ubuntu"
        result = _is_wsl()
        assert result is True
    finally:
        if old_wsl is None:
            os.environ.pop("WSL_DISTRO_NAME", None)
        else:
            os.environ["WSL_DISTRO_NAME"] = old_wsl


def test_is_wsl_true_via_proc_version():
    """_is_wsl() — возвращает True по содержимому /proc/version."""
    from breaker.ui.timer import _is_wsl
    import os
    old_wsl = os.environ.pop("WSL_DISTRO_NAME", None)
    try:
        from unittest.mock import mock_open
        with patch("builtins.open", mock_open(read_data="Linux version microsoft-standard-WSL2")):
            result = _is_wsl()
        assert result is True
    finally:
        if old_wsl is not None:
            os.environ["WSL_DISTRO_NAME"] = old_wsl


def test_linux_path_to_windows_with_wslpath():
    """_linux_path_to_windows() — конвертация через wslpath."""
    from breaker.ui.timer import _linux_path_to_windows
    from pathlib import Path
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "C:\\Users\\test\\file.wav\n"
    with patch("subprocess.run", return_value=mock_result):
        result = _linux_path_to_windows(Path("/mnt/c/Users/test/file.wav"))
    assert result == "C:\\Users\\test\\file.wav"


def test_linux_path_to_windows_fallback():
    """_linux_path_to_windows() — ручная конвертация /mnt/c/..."""
    from breaker.ui.timer import _linux_path_to_windows
    from pathlib import Path
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _linux_path_to_windows(Path("/mnt/c/Users/test/file.wav"))
    assert result == "C:\\Users\\test\\file.wav"


def test_linux_path_to_windows_non_mnt():
    """_linux_path_to_windows() — путь не из /mnt/."""
    from breaker.ui.timer import _linux_path_to_windows
    from pathlib import Path
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _linux_path_to_windows(Path("/home/user/file.wav"))
    assert result == "/home/user/file.wav"


@patch("breaker.ui.timer.sys.platform", "win32")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_windows_with_file(mock_run, capsys):
    """_play_sound() на Windows с существующим файлом — PowerShell."""
    from breaker.ui.timer import _play_sound
    with patch("pathlib.Path.exists", return_value=True):
        with patch("breaker.ui.timer._is_wsl", return_value=False):
            _play_sound()
    # На Windows должен вызваться PowerShell
    if mock_run.called:
        call_args = mock_run.call_args
        assert "powershell" in str(call_args).lower()


@patch("breaker.ui.timer.sys.platform", "darwin")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_macos_with_file(mock_run, capsys):
    """_play_sound() на macOS с существующим файлом — afplay."""
    from breaker.ui.timer import _play_sound
    with patch("pathlib.Path.exists", return_value=True):
        with patch("breaker.ui.timer._is_wsl", return_value=False):
            _play_sound()
    if mock_run.called:
        call_args = mock_run.call_args
        assert call_args.args[0][0] == "afplay"


@patch("breaker.ui.timer.sys.platform", "linux")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_linux_with_file(mock_run, capsys):
    """_play_sound() на Linux с существующим файлом."""
    from breaker.ui.timer import _play_sound
    with patch("pathlib.Path.exists", return_value=True):
        with patch("breaker.ui.timer._is_wsl", return_value=False):
            mock_run.return_value = MagicMock(returncode=0)
            _play_sound()


@patch("breaker.ui.timer.sys.platform", "win32")
def test_play_sound_file_not_found_windows(capsys):
    """_play_sound() на Windows без файла — fallback на системный звук."""
    import sys
    from unittest.mock import MagicMock
    
    # Создаём фейковый модуль winsound (его нет на macOS)
    mock_winsound = MagicMock()
    
    with patch.dict(sys.modules, {"winsound": mock_winsound}):
        from breaker.ui.timer import _play_sound
        with patch("pathlib.Path.exists", return_value=False):
            with patch("breaker.ui.timer._is_wsl", return_value=False):
                _play_sound()
    
    # Проверяем, что был вызван системный звук
    mock_winsound.Beep.assert_called_once_with(1000, 500)


@patch("breaker.ui.timer.sys.platform", "darwin")
@patch("breaker.ui.timer.subprocess.run")
def test_play_system_sound_macos(mock_run):
    """_play_system_sound() на macOS — Glass.aiff."""
    from breaker.ui.timer import _play_system_sound
    _play_system_sound()
    call_args = mock_run.call_args
    assert "Glass.aiff" in str(call_args)


@patch("breaker.ui.timer.sys.platform", "win32")
def test_play_system_sound_windows():
    """_play_system_sound() на Windows — winsound.Beep."""
    import sys
    from unittest.mock import MagicMock
    
    # Создаём фейковый модуль winsound
    mock_winsound = MagicMock()
    
    with patch.dict(sys.modules, {"winsound": mock_winsound}):
        from breaker.ui.timer import _play_system_sound
        _play_system_sound()
    
    # Проверяем, что Beep был вызван с правильными параметрами
    mock_winsound.Beep.assert_called_once_with(1000, 500)


@patch("breaker.ui.timer.sys.platform", "linux")
def test_play_system_sound_linux(capsys):
    """_play_system_sound() на Linux — bell символ."""
    from breaker.ui.timer import _play_system_sound
    _play_system_sound()
    captured = capsys.readouterr()
    assert "\a" in captured.out


@patch("breaker.ui.timer._is_wsl", return_value=True)
@patch("breaker.ui.timer._play_sound_wsl")
def test_play_sound_wsl_delegates(mock_play_wsl, mock_is_wsl):
    """_play_sound() в WSL — делегирует в _play_sound_wsl()."""
    from breaker.ui.timer import _play_sound
    _play_sound()
    mock_play_wsl.assert_called_once()


@patch("breaker.ui.timer.sys.platform", "win32")
@patch("breaker.ui.timer.subprocess.run")
def test_play_sound_wsl_with_file(mock_run, capsys):
    """_play_sound_wsl() с существующим файлом."""
    from breaker.ui.timer import _play_sound_wsl
    from pathlib import Path
    with patch("pathlib.Path.exists", return_value=True):
        with patch("breaker.ui.timer._linux_path_to_windows", return_value="C:\\file.wav"):
            _play_sound_wsl(Path("/mnt/c/file.wav"))
    if mock_run.called:
        call_args = mock_run.call_args
        assert "powershell.exe" in str(call_args).lower()


@patch("breaker.ui.timer.sys.platform", "win32")
@patch("breaker.ui.timer.subprocess.run")
def test_play_system_sound_wsl(mock_run):
    """_play_system_sound_wsl() — системный beep через PowerShell."""
    from breaker.ui.timer import _play_system_sound_wsl
    _play_system_sound_wsl()
    if mock_run.called:
        call_args = mock_run.call_args
        assert "powershell.exe" in str(call_args).lower()


@patch("rich.prompt.IntPrompt.ask", side_effect=[0, -5, 5])
def test_ask_duration_below_minimum_then_valid(mock_input):
    """ask_duration() — значение ниже минимума, потом валидное."""
    from breaker.ui.timer import ask_duration
    result = ask_duration()
    assert result == 5


@patch("rich.prompt.IntPrompt.ask", side_effect=[100, 51, 25])
def test_ask_duration_above_maximum_then_valid(mock_input):
    """ask_duration() — значение выше максимума, потом валидное."""
    from breaker.ui.timer import ask_duration
    result = ask_duration()
    assert result == 25


@patch("breaker.ui.timer.time.sleep")
@patch("rich.prompt.IntPrompt.ask", return_value=5)
def test_pomodoro_timer_interrupted(mock_input, mock_sleep, capsys):
    """pomodoro_timer() — прерывание через KeyboardInterrupt."""
    from breaker.ui.timer import pomodoro_timer
    mock_sleep.side_effect = KeyboardInterrupt()
    result = pomodoro_timer(minutes=5)
    assert result is False
    captured = capsys.readouterr()
    assert "прерван" in captured.out.lower()