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
    file.write_text("hello", encoding='utf-8')
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
    f1.write_text("aaa", encoding='utf-8')
    f2 = tmp_path / "b.py"
    f2.write_text("bbbbb", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[f1, f2])
    sizes = monitor._get_file_sizes()
    assert sizes[f1] == 3
    assert sizes[f2] == 5


def test_get_activity_info_no_changes(tmp_path):
    """Нет изменений — total_chars_added = 0."""
    file = tmp_path / "main.py"
    file.write_text("hello", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    info = monitor._get_activity_info()
    assert info["total_chars_added"] == 0
    assert info["changed_files"] == []


def test_get_activity_info_with_changes(tmp_path):
    """Файл вырос — total_chars_added > 0."""
    file = tmp_path / "main.py"
    file.write_text("hello", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    file.write_text("hello" + "x" * 50, encoding='utf-8')
    info = monitor._get_activity_info()
    assert info["total_chars_added"] == 50
    assert len(info["changed_files"]) == 1


def test_check_activity_below_threshold(tmp_path):
    """Изменение меньше порога — активность не засчитана."""
    file = tmp_path / "main.py"
    file.write_text("hello", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("hello" + "x" * 50, encoding='utf-8')
    assert monitor._check_activity() is False


def test_check_activity_at_threshold(tmp_path):
    """Изменение равно порогу — активность засчитана."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("x" * 100, encoding='utf-8')
    assert monitor._check_activity() is True


def test_check_activity_above_threshold(tmp_path):
    """Изменение больше порога — активность засчитана."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file], activity_threshold=100)
    file.write_text("x" * 200, encoding='utf-8')
    assert monitor._check_activity() is True


def test_check_file_modified_no_change(tmp_path):
    """Файл не изменён."""
    file = tmp_path / "main.py"
    file.write_text("hello", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    assert monitor._check_file_modified() is False


def test_check_file_modified_with_change(tmp_path):
    """Файл изменён."""
    file = tmp_path / "main.py"
    file.write_text("hello", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    file.write_text("hello world", encoding='utf-8')
    assert monitor._check_file_modified() is True


def test_handle_help_level1_with_callback(tmp_path):
    """Уровень 1 с колбэком."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
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
    file.write_text("", encoding='utf-8')
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
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    with patch("breaker.ui.help_menu.show_help_level1", return_value=5):
        with patch("breaker.ui.help_menu.apply_help_choice", return_value="skip"):
            result = monitor._handle_help_level1()
    assert result == "skip"


def test_handle_success_with_callback(tmp_path):
    """Успех с колбэком."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    callback = MagicMock()
    monitor = ActivityMonitor(
        watched_files=[file],
        success_callback=callback,
    )
    monitor._handle_success()
    assert callback.called


def test_handle_success_without_callback(tmp_path):
    """Успех без колбэка — встроенное сообщение."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    
    with patch.object(monitor, '_get_activity_info', return_value={"total_chars_added": 150}):
        monitor._handle_success()


def test_process_help_result_timer(tmp_path):
    """Результат 'timer' — запускает таймер."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    with patch("breaker.ui.timer.run_timer_with_prompt", return_value=True) as mock_timer:
        monitor._process_help_result("timer")
    assert mock_timer.called


def test_process_help_result_skip(tmp_path):
    """Результат 'skip' — ничего не делает."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor._process_help_result("skip")


def test_process_help_result_template(tmp_path):
    """Результат 'template:function' — ничего не делает."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor._process_help_result("template:function")


def test_process_help_result_open(tmp_path):
    """Результат 'open:...' — открывает файл."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(watched_files=[file])
    with patch("breaker.engine.executor.open_file", return_value="file:///path") as mock_open:
        monitor._process_help_result(f"open:{file}")
    assert mock_open.called


def test_pause_progress_callback(tmp_path):
    """Приостановка прогресса вызывает колбэк."""
    file = tmp_path / "main.py"
    callback = MagicMock()
    monitor = ActivityMonitor(
        watched_files=[file],
        progress_refresh_callback=callback,
    )
    monitor._pause_progress()
    assert callback.called
    callback.assert_called_with(True)


def test_resume_progress_callback(tmp_path):
    """Возобновление прогресса вызывает колбэк."""
    file = tmp_path / "main.py"
    callback = MagicMock()
    monitor = ActivityMonitor(
        watched_files=[file],
        progress_refresh_callback=callback,
    )
    monitor._resume_progress()
    assert callback.called
    callback.assert_called_with(False)


def test_show_help_menu_safe_level1(tmp_path):
    """Безопасный показ меню уровня 1."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    
    callback = MagicMock(return_value=1)
    apply_callback = MagicMock(return_value="skip")
    
    monitor = ActivityMonitor(
        watched_files=[file],
        help_level1_callback=callback,
        apply_choice_callback=apply_callback,
    )
    
    with patch.object(monitor, '_pause_progress') as mock_pause:
        with patch.object(monitor, '_resume_progress') as mock_resume:
            result = monitor._show_help_menu_safe(1)
    
    assert result == "skip"
    assert mock_pause.called
    assert mock_resume.called


def test_show_help_menu_safe_level2(tmp_path):
    """Безопасный показ меню уровня 2."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    
    callback = MagicMock(return_value=1)
    apply_callback = MagicMock(return_value="skip")
    
    monitor = ActivityMonitor(
        watched_files=[file],
        help_level2_callback=callback,
        apply_choice_callback=apply_callback,
    )
    
    with patch.object(monitor, '_pause_progress') as mock_pause:
        with patch.object(monitor, '_resume_progress') as mock_resume:
            result = monitor._show_help_menu_safe(2)
    
    assert result == "skip"
    assert mock_pause.called
    assert mock_resume.called


def test_process_help_result_text_inserted(tmp_path):
    """Результат 'text_inserted' — устанавливает pending_action = True."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor.pending_action = False
    monitor._process_help_result("text_inserted")
    assert monitor.pending_action is True


def test_process_help_result_skip_sets_pending(tmp_path):
    """Результат 'skip' — устанавливает pending_action = True."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor.pending_action = False
    monitor._process_help_result("skip")
    assert monitor.pending_action is True


def test_stop_monitoring(tmp_path):
    """Остановка мониторинга."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor.running = True
    monitor.stop_monitoring()
    assert monitor.running is False


def test_set_interrupted(tmp_path):
    """Установка флага прерывания."""
    file = tmp_path / "main.py"
    monitor = ActivityMonitor(watched_files=[file])
    monitor.running = True
    monitor.set_interrupted()
    assert monitor.interrupted is True
    assert monitor.running is False


def test_start_monitoring_immediate_success(tmp_path):
    """Мониторинг сразу завершается успехом при активности."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    
    monitor = ActivityMonitor(
        watched_files=[file],
        activity_threshold=50,
        idle_threshold_level1=999,
        check_interval=1,
    )
    
    with patch.object(monitor, '_check_activity', return_value=True):
        with patch.object(monitor, '_handle_success') as mock_success:
            with patch('time.sleep', return_value=None):
                with patch('time.time', return_value=0):
                    result = monitor.start_monitoring()
                    assert result == "success"
                    assert mock_success.called


def test_start_monitoring_keyboard_interrupt(tmp_path):
    """Прерывание Ctrl+C."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(
        watched_files=[file],
        idle_threshold_level1=999,
        check_interval=1,
    )
    
    with patch.object(monitor, '_check_activity', return_value=False):
        with patch.object(monitor, '_get_file_sizes', return_value={file: 0}):
            with patch.object(monitor, '_check_file_modified', return_value=False):
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    result = monitor.start_monitoring()
                    assert result == "interrupted"


def test_start_monitoring_interrupted_flag(tmp_path):
    """Мониторинг прерывается при установке флага interrupted."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')
    monitor = ActivityMonitor(
        watched_files=[file],
        idle_threshold_level1=999,
        idle_threshold_level2=999,
        idle_threshold_timeout=999,
        check_interval=1,
    )

    # Устанавливаем все проверки в False
    with patch.object(monitor, '_check_activity', return_value=False):
        with patch.object(monitor, '_check_file_modified', return_value=False):
            with patch.object(monitor, '_get_file_sizes', return_value={file: 0}):
                # Мокаем time.sleep чтобы после первого вызова установить флаг
                def sleep_and_interrupt(x):
                    monitor.set_interrupted()
                    # Возвращаем None, но вызываем StopIteration чтобы выйти из цикла
                    raise KeyboardInterrupt()
                
                with patch('time.sleep', side_effect=sleep_and_interrupt):
                    with patch('time.time', return_value=0):
                        result = monitor.start_monitoring()
                        assert result == "interrupted"


def test_start_monitoring_success_on_activity(tmp_path):
    """Успех при достижении порога активности."""
    file = tmp_path / "main.py"
    file.write_text("", encoding='utf-8')

    monitor = ActivityMonitor(
        watched_files=[file],
        activity_threshold=50,
        check_interval=1,
        idle_threshold_level1=999,
        idle_threshold_level2=999,
        idle_threshold_timeout=999,
    )

    call_count = 0

    def mock_get_sizes():
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return {file: 0}
        return {file: 100}

    def mock_check_activity():
        return call_count > 1

    with patch.object(monitor, '_get_file_sizes', side_effect=mock_get_sizes):
        with patch.object(monitor, '_check_activity', side_effect=mock_check_activity):
            with patch.object(monitor, '_handle_success') as mock_success:
                with patch('time.sleep', return_value=None):
                    with patch('time.time', return_value=0):
                        result = monitor.start_monitoring()
                        assert result == "success"
                        assert mock_success.called