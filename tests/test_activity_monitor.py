import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from breaker.ui.activity_monitor import ActivityMonitor



def test_init_defaults():
    """Инициализация с параметрами по умолчанию."""
    monitor = ActivityMonitor(watched_files=[Path("main.py")])
    assert monitor.idle_threshold_level1 == 60
    assert monitor.idle_threshold_level2 == 180
    assert monitor.idle_threshold_timeout == 300
    assert monitor.activity_threshold == 100
    assert monitor.check_interval == 10
    assert monitor.help_level == 0
    assert monitor.help_count == 0


def test_init_custom_params():
    """Инициализация с пользовательскими параметрами."""
    monitor = ActivityMonitor(
        watched_files=[Path("main.py")],
        idle_threshold_level1=30,
        idle_threshold_level2=90,
        activity_threshold=50,
    )
    assert monitor.idle_threshold_level1 == 30
    assert monitor.idle_threshold_level2 == 90
    assert monitor.activity_threshold == 50



def test_get_file_sizes_existing_file(tmp_path):
    """Размер существующего файла."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file])
    sizes = monitor._get_file_sizes()
    assert sizes[file] == 5


def test_get_file_sizes_nonexistent_file(tmp_path):
    """Несуществующий файл имеет размер 0."""
    file = tmp_path / "missing.py"
    monitor = ActivityMonitor(watched_files=[file])
    sizes = monitor._get_file_sizes()
    assert sizes[file] == 0


def test_get_file_sizes_multiple_files(tmp_path):
    """Несколько файлов."""
    f1 = tmp_path / "a.py"
    f1.write_text("aaa")
    f2 = tmp_path / "b.py"
    f2.write_text("bbbbb")
    monitor = ActivityMonitor(watched_files=[f1, f2])
    sizes = monitor._get_file_sizes()
    assert sizes[f1] == 3
    assert sizes[f2] == 5


def test_get_activity_info_no_changes(tmp_path):
    """Нет изменений — total_chars_added = 0."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file])
    info = monitor._get_activity_info()
    assert info["total_chars_added"] == 0
    assert info["changed_files"] == []


def test_get_activity_info_with_changes(tmp_path):
    """Файл вырос — total_chars_added > 0."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file])
    # Имитируем изменение
    file.write_text("hello" + "x" * 50)
    info = monitor._get_activity_info()
    assert info["total_chars_added"] == 50
    assert len(info["changed_files"]) == 1


def test_check_activity_below_threshold(tmp_path):
    """Изменение меньше порога — активность не засчитана."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("hello" + "x" * 50)
    assert monitor._check_activity() is False


def test_check_activity_at_threshold(tmp_path):
    """Изменение равно порогу — активность засчитана."""
    file = tmp_path / "main.py"
    file.write_text("")
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("x" * 100)
    assert monitor._check_activity() is True


def test_check_activity_above_threshold(tmp_path):
    """Изменение больше порога — активность засчитана."""
    file = tmp_path / "main.py"
    file.write_text("")
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("x" * 200)
    assert monitor._check_activity() is True


def test_check_file_modified_no_change(tmp_path):
    """Файл не изменён."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file])
    assert monitor._check_file_modified() is False


def test_check_file_modified_with_change(tmp_path):
    """Файл изменён."""
    file = tmp_path / "main.py"
    file.write_text("hello")
    monitor = ActivityMonitor(watched_files=[file])
    file.write_text("hello world")
    assert monitor._check_file_modified() is True


def test_handle_help_level1_with_callback(tmp_path):
    """Уровень 1 с колбэком."""
    file = tmp_path / "main.py"
    file.write_text("")
    callback = MagicMock(return_value=1)
    apply_callback = MagicMock(return_value="template:function")
    monitor = ActivityMonitor(
        watched_files=[file],
        help_level1_callback=callback,
        apply_choice_callback=apply_callback,
    )
    result = monitor._handle_help_level1()
    assert result == "template:function"
    assert callback.called
    assert apply_callback.called
    assert monitor.help_level == 1
    assert monitor.help_count == 1


def test_handle_help_level2_with_callback(tmp_path):
    """Уровень 2 с колбэком."""
    file = tmp_path / "main.py"
    file.write_text("")
    callback = MagicMock(return_value=3)
    apply_callback = MagicMock(return_value="text_inserted")
    monitor = ActivityMonitor(
        watched_files=[file],
        help_level2_callback=callback,
        apply_choice_callback=apply_callback,
    )
    result = monitor._handle_help_level2()
    assert result == "text_inserted"
    assert callback.called
    assert monitor.help_level == 2


def test_handle_help_level1_without_callback(tmp_path):
    """Уровень 1 без колбэка — используется fallback."""
    file = tmp_path / "main.py"
    file.write_text("")
    monitor = ActivityMonitor(watched_files=[file])
    with patch("breaker.ui.help_menu.show_help_level1", return_value=5):
        result = monitor._handle_help_level1()
    assert result == "skip"


def test_handle_success_with_callback(tmp_path, capsys):
    """Успех с колбэком."""
    file = tmp_path / "main.py"
    file.write_text("")
    callback = MagicMock()
    monitor = ActivityMonitor(
        watched_files=[file],
        success_callback=callback,
    )
    monitor._handle_success()
    assert callback.called


def test_handle_success_without_callback(tmp_path, capsys):
    """Успех без колбэка — встроенное сообщение."""
    file = tmp_path / "main.py"
    file.write_text("")
    monitor = ActivityMonitor(watched_files=[file])
    monitor._handle_success()
    captured = capsys.readouterr()
    assert "Отлично" in captured.out


def test_process_help_result_timer(tmp_path, capsys):
    """Результат 'timer' — запускает таймер."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    with patch("breaker.ui.timer.run_timer_with_prompt", return_value=True) as mock_timer:
        monitor._process_help_result("timer")
    assert mock_timer.called


def test_process_help_result_skip(tmp_path, capsys):
    """Результат 'skip' — ничего не делает."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor._process_help_result("skip")
    # Никаких ошибок


def test_process_help_result_template(tmp_path, capsys):
    """Результат 'template:function' — ничего не делает (шаблон уже вставлен)."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor._process_help_result("template:function")


@patch("time.sleep")
@patch("time.time")
def test_start_monitoring_success_on_activity(mock_time, mock_sleep, tmp_path):
    """Успех при достижении порога активности."""
    file = tmp_path / "main.py"
    file.write_text("")

    # Имитируем время: 0, 1, 2, ... (каждый вызов time.time() возвращает следующее значение)
    mock_time.side_effect = [
        0,     # session_start_time
        0,     # last_activity_time
        0,     # _get_file_sizes (baseline)
        10,    # первая итерация: idle_time = 10
        10,    # _check_activity (сравнение)
        20,    # вторая итерация: idle_time = 20
        20,    # _check_activity
    ]

    monitor = ActivityMonitor(
        watched_files=[file],
        activity_threshold=50,
        check_interval=10,
    )

    # Имитируем рост файла
    original_get_sizes = monitor._get_file_sizes
    call_count = [0]

    def mock_get_sizes():
        call_count[0] += 1
        if call_count[0] <= 1:
            return {file: 0}  # baseline
        return {file: 100}  # активность

    monitor._get_file_sizes = mock_get_sizes

    result = monitor.start_monitoring()
    assert result == "success"


from itertools import count

@patch("time.sleep")
@patch("time.time")
def test_start_monitoring_timeout(mock_time, mock_sleep, tmp_path):
    """Таймаут при длительном бездействии."""
    file = tmp_path / "main.py"
    file.write_text("")

    # Используем бесконечный счётчик для time.time()
    time_counter = count(1, 1)  # 1, 2, 3, 4, ...
    mock_time.side_effect = lambda: next(time_counter)

    monitor = ActivityMonitor(
        watched_files=[file],
        idle_threshold_level1=2,
        idle_threshold_level2=5,
        idle_threshold_timeout=8,
        activity_threshold=100,
        check_interval=1,
        help_level1_callback=MagicMock(return_value=5),  # skip
        help_level2_callback=MagicMock(return_value=6),  # skip
        apply_choice_callback=MagicMock(return_value="skip"),
    )

    result = monitor.start_monitoring()
    assert result == "timeout"

@patch("time.sleep")
def test_start_monitoring_keyboard_interrupt(mock_sleep, tmp_path):
    """Прерывание Ctrl+C."""
    file = tmp_path / "main.py"
    file.write_text("")
    monitor = ActivityMonitor(watched_files=[file])
    mock_sleep.side_effect = KeyboardInterrupt()
    result = monitor.start_monitoring()
    assert result == "stopped"



def test_stop_monitoring(tmp_path, capsys):
    """Остановка мониторинга."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor.running = True
    monitor.stop_monitoring()
    assert monitor.running is False
    captured = capsys.readouterr()
    assert "остановлен" in captured.out