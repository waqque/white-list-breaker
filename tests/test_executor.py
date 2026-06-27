"""Тесты для engine/executor.py.

Проверяют:
- Кроссплатформенность open_file() 
- Интеграцию со schema.py 
- Обработку ошибок 
"""

import platform
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from breaker.engine.executor import open_file, execute_ritual, run_shell, create_test
from breaker.engine.exceptions import (
    BreakerFileNotFoundError,
    CommandNotFoundError,
    CommandTimeoutError,
    CommandFailedError,
)

from breaker.core.schema import Ritual, ActionType, RitualResult


# Тесты для open_file()

class TestOpenFile:
    """Тесты функции open_file."""

    def test_file_not_found_raises(self, tmp_path: Path):
        """Если файла нет — BreakerFileNotFoundError."""
        missing = tmp_path / "does_not_exist.txt"
        assert not missing.exists()
        
        with pytest.raises(BreakerFileNotFoundError) as exc_info:
            open_file(missing)
        
        assert "Файл не найден" in str(exc_info.value)

    def test_directory_raises(self, tmp_path: Path):
        """Если указан путь к директории — ошибка."""
        directory = tmp_path / "some_dir"
        directory.mkdir()
        
        with pytest.raises(BreakerFileNotFoundError) as exc_info:
            open_file(directory)
        
        assert "директории" in str(exc_info.value)

    def test_empty_path_raises(self):
        """Пустой путь — ValueError."""
        with pytest.raises(ValueError) as exc_info:
            open_file("")
        
        assert "cannot be empty" in str(exc_info.value)

    def test_open_with_vscode(self, tmp_path: Path):
        """Открытие файла через VS Code — вызывается `code <path>`."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = open_file(file, editor="code")

            assert result == f"file://{file.resolve()}"
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["code", str(file.resolve())]

    def test_editor_not_found_raises(self, tmp_path: Path):
        """Если редактор не установлен — CommandNotFoundError."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("No such file")
            with pytest.raises(CommandNotFoundError):
                open_file(file, editor="nonexistent-editor")

    def test_editor_timeout_raises(self, tmp_path: Path):
        """Если редактор завис — CommandTimeoutError."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="code", timeout=10)
            with pytest.raises(CommandTimeoutError):
                open_file(file, editor="code", timeout=10)

    def test_system_default_windows(self, tmp_path: Path):
        """На Windows вызывается os.startfile."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.platform.system", return_value="Windows"):
            # create=True нужен, потому что os.startfile существует только на Windows
            with patch("breaker.engine.executor.os.startfile", create=True) as mock_start:
                result = open_file(file, editor=None)
                assert result == f"file://{file.resolve()}"
                mock_start.assert_called_once_with(str(file.resolve()))

    def test_system_default_macos(self, tmp_path: Path):
        """На macOS вызывается `open <path>`."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.platform.system", return_value="Darwin"):
            with patch("breaker.engine.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = open_file(file, editor=None)
                assert result == f"file://{file.resolve()}"
                args, _ = mock_run.call_args
                assert args[0] == ["open", str(file.resolve())]

    def test_system_default_linux(self, tmp_path: Path):
        """На Linux вызывается `xdg-open <path>`."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.platform.system", return_value="Linux"):
            with patch("breaker.engine.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = open_file(file, editor=None)
                assert result == f"file://{file.resolve()}"
                args, _ = mock_run.call_args
                assert args[0] == ["xdg-open", str(file.resolve())]

    def test_unsupported_os_raises(self, tmp_path: Path):
        """На неизвестной ОС — CommandNotFoundError."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor.platform.system", return_value="FreeBSD"):
            with pytest.raises(CommandNotFoundError):
                open_file(file, editor=None)


# Тесты для execute_ritual() 

class TestExecuteRitual:
    """Тесты интеграции executor со schema.py."""

    def test_execute_open_file_success(self, tmp_path: Path):
        """execute_ritual() с OPEN_FILE возвращает успешный RitualResult."""
        file = tmp_path / "example.py"
        file.write_text("# test")

        ritual = Ritual(
            signal="файл пуст",
            action="открыть файл",
            target=str(file),
            action_type=ActionType.OPEN_FILE,
        )

        with patch("breaker.engine.executor._open_in_editor") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = execute_ritual(ritual)

            assert isinstance(result, RitualResult)
            assert result.success is True
            assert result.ritual == ritual
            assert result.evidence_link == f"file://{file.resolve()}"
            assert result.finished_at is not None

    def test_execute_open_file_error(self, tmp_path: Path):
        """execute_ritual() с ошибкой возвращает RitualResult с error_message."""
        file = tmp_path / "example.py"
        file.write_text("# test") 

        ritual = Ritual(
            signal="файл пуст",
            action="открыть файл",
            target=str(file),
            action_type=ActionType.OPEN_FILE,
        )

        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.side_effect = CommandNotFoundError("Editor not found")
            result = execute_ritual(ritual)

            assert isinstance(result, RitualResult)
            assert result.success is False
            assert "Editor not found" in result.error_message
            assert result.finished_at is not None

# Тесты для run_shell() 


class TestRunShell:

    def test_simple_command_succeeds(self):
        """Простая команда (echo) """
        result = run_shell("echo 'hello'")
        assert result == "shell://echo 'hello'"

    def test_command_with_cwd(self, tmp_path: Path):
        """Команда выполняется в указанной директории."""
        # Используем python -c вместо pwd для кроссплатформенности
        result = run_shell(
            "python -c \"import os; print(os.getcwd())\"", cwd=tmp_path
        )
        assert result.startswith("shell://")

    def test_empty_command_raises(self):
        """Пустая команда — ValueError."""
        with pytest.raises(ValueError) as exc_info:
            run_shell("")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_command_raises(self):
        """Команда из пробелов — ValueError."""
        with pytest.raises(ValueError) as exc_info:
            run_shell("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_dangerous_command_raises(self):
        """Опасная команда (rm -rf /) — ValueError."""
        with pytest.raises(ValueError) as exc_info:
            run_shell("rm -rf /")
        assert "Dangerous command" in str(exc_info.value)

    def test_dangerous_format_command_raises(self):
        """Опасная команда (format c:) — ValueError."""
        with pytest.raises(ValueError) as exc_info:
            run_shell("format c:")
        assert "Dangerous command" in str(exc_info.value)

    def test_command_not_found_raises(self):
        """Несуществующая команда - CommandFailedError."""
        with pytest.raises(CommandFailedError) as exc_info:
            run_shell("nonexistent_command_xyz_12345_qwerty")
        assert exc_info.value.returncode != 0

    def test_command_timeout_raises(self):
        """Команда, которая спит дольше таймаута — CommandTimeoutError."""
        cmd = "sleep 10" if platform.system() != "Windows" else "timeout 10"
        with pytest.raises(CommandTimeoutError):
            run_shell(cmd, timeout=1)

    def test_failing_command_raises(self):
        """Команда с ненулевым exit code — CommandFailedError."""
        with pytest.raises(CommandFailedError) as exc_info:
            run_shell("exit 42")
        assert exc_info.value.returncode == 42


# Тесты для create_test() 


class TestCreateTest:
    """Тесты функции create_test.
    """

    def test_create_with_pytest_template(self, tmp_path: Path):
        """Создание файла с шаблоном pytest."""
        file = tmp_path / "test_example.py"
        result = create_test(file, template="pytest")

        assert result == f"file://{file.resolve()}"
        assert file.exists()
        content = file.read_text()
        assert "def test_placeholder" in content
        assert "assert True" in content

    def test_create_with_unittest_template(self, tmp_path: Path):
        """Создание файла с шаблоном unittest."""
        file = tmp_path / "test_example.py"
        result = create_test(file, template="unittest")

        assert result == f"file://{file.resolve()}"
        assert file.exists()
        content = file.read_text()
        assert "import unittest" in content
        assert "class Test" in content

    def test_create_with_custom_content(self, tmp_path: Path):
        """Создание файла с кастомным содержимым."""
        file = tmp_path / "custom.txt"
        content = "Hello, World!"
        result = create_test(file, content=content)

        assert result == f"file://{file.resolve()}"
        assert file.exists()
        assert file.read_text() == content

    def test_create_creates_parent_dirs(self, tmp_path: Path):
        """Создание файла в несуществующей директории."""
        file = tmp_path / "deep" / "nested" / "dir" / "test.py"
        result = create_test(file)

        assert result == f"file://{file.resolve()}"
        assert file.exists()
        assert file.parent.exists()

    def test_create_refuses_to_overwrite(self, tmp_path: Path):
        """Если файл уже существует — FileExistsError."""
        file = tmp_path / "existing.py"
        file.write_text("original")

        with pytest.raises(FileExistsError):
            create_test(file)

    def test_unknown_template_raises(self, tmp_path: Path):
        """Неизвестный шаблон — ValueError."""
        file = tmp_path / "test.py"
        with pytest.raises(ValueError):
            create_test(file, template="nonexistent_template")

    def test_empty_template(self, tmp_path: Path):
        """Шаблон 'empty' создаёт пустой файл."""
        file = tmp_path / "empty.txt"
        result = create_test(file, template="empty")

        assert result == f"file://{file.resolve()}"
        assert file.exists()
        assert file.read_text() == ""


# Расширенные тесты execute_ritual() 


class TestExecuteRitualExtended:
    """Расширенные тесты execute_ritual() для всех типов действий."""

    def test_execute_run_shell_success(self, tmp_path: Path):
        """execute_ritual() с RUN_SHELL возвращает успешный RitualResult."""
        ritual = Ritual(
            signal="нужно запустить тесты",
            action="выполнить echo",
            target="echo 'running tests'",
            action_type=ActionType.RUN_SHELL,
        )

        result = execute_ritual(ritual)

        assert isinstance(result, RitualResult)
        assert result.success is True
        assert result.ritual == ritual
        assert result.evidence_link.startswith("shell://")
        assert result.finished_at is not None

    def test_execute_run_shell_error(self, tmp_path: Path):
        """execute_ritual() с RUN_SHELL и ошибкой — RitualResult с error_message."""
        ritual = Ritual(
            signal="команда не работает",
            action="запустить несуществующую команду",
            target="nonexistent_command_xyz_12345",
            action_type=ActionType.RUN_SHELL,
        )

        result = execute_ritual(ritual)

        assert isinstance(result, RitualResult)
        assert result.success is False
        assert result.error_message is not None
        assert result.finished_at is not None

    def test_execute_create_test_success(self, tmp_path: Path):
        """execute_ritual() с CREATE_TEST создаёт файл и возвращает успешный RitualResult."""
        test_file = tmp_path / "test_new.py"

        ritual = Ritual(
            signal="нет тестов",
            action="создать тест",
            target=str(test_file),
            action_type=ActionType.CREATE_TEST,
        )

        result = execute_ritual(ritual)

        assert isinstance(result, RitualResult)
        assert result.success is True
        assert result.ritual == ritual
        assert result.evidence_link == f"file://{test_file.resolve()}"
        assert test_file.exists()
        assert "def test_placeholder" in test_file.read_text()
        assert result.finished_at is not None

    def test_execute_create_test_error(self, tmp_path: Path):
        """execute_ritual() с CREATE_TEST и существующим файлом — ошибка."""
        test_file = tmp_path / "existing.py"
        test_file.write_text("# existing")

        ritual = Ritual(
            signal="нет тестов",
            action="создать тест",
            target=str(test_file),
            action_type=ActionType.CREATE_TEST,
        )

        result = execute_ritual(ritual)

        assert isinstance(result, RitualResult)
        assert result.success is False
        assert "already exists" in result.error_message
        assert result.finished_at is not None