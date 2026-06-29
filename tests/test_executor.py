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

from breaker.engine.executor import open_file, execute_ritual, create_test
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

    def test_editor_not_found_fallback_to_system(self, tmp_path: Path):
        """Если редактор не установлен — fallback на системное приложение."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor._open_in_editor") as mock_editor:
            mock_editor.side_effect = CommandNotFoundError("Editor not found")

            with patch("breaker.engine.executor._open_system_default") as mock_system:
                mock_system.return_value = f"file://{file.resolve()}"

                result = open_file(file, editor="nonexistent-editor")

                # Проверяем, что вызвался fallback
                mock_system.assert_called_once()
                assert result == f"file://{file.resolve()}"

    def test_explicit_editor_not_found_raises(self, tmp_path: Path):
        """Если явно указан editor=None и системное приложение не найдено — ошибка."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor._open_system_default") as mock_system:
            mock_system.side_effect = CommandNotFoundError("System opener not found")

            with pytest.raises(CommandNotFoundError):
                open_file(file, editor=None)

    def test_fallback_when_editor_not_in_path(self, tmp_path: Path):
        """Проверяем, что модуль работает даже если 'code' не в PATH."""
        file = tmp_path / "test.py"
        file.write_text("print('hi')")

        with patch("breaker.engine.executor._open_in_editor") as mock_editor:
            mock_editor.side_effect = CommandNotFoundError("Editor 'code' not found")

            with patch("breaker.engine.executor._open_system_default") as mock_system:
                mock_system.return_value = f"file://{file.resolve()}"

                result = open_file(file)

                # Проверяем, что вызвался fallback
                mock_editor.assert_called_once()
                mock_system.assert_called_once()
                assert result == f"file://{file.resolve()}"

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


# Тесты для create_test()


class TestCreateTest:
    """Тесты функции create_test.

    Все тесты используют tmp_path, поэтому созданные файлы
    НЕ попадают в репозиторий и автоматически удаляются pytest.
    
    ВАЖНО: все тесты мокают open_file(), чтобы не запускать
    реальный редактор во время тестов.
    """

    def test_create_with_pytest_template(self, tmp_path: Path):
        """Создание файла с шаблоном pytest."""
        file = tmp_path / "test_example.py"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, template="pytest")

            assert result == f"file://{file.resolve()}"
            assert file.exists()
            content = file.read_text()
            assert "def test_placeholder" in content
            assert "assert True" in content
            mock_open.assert_called_once()

    def test_create_with_unittest_template(self, tmp_path: Path):
        """Создание файла с шаблоном unittest."""
        file = tmp_path / "test_example.py"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
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
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, content=content)

            assert result == f"file://{file.resolve()}"
            assert file.exists()
            assert file.read_text() == content

    def test_create_creates_parent_dirs(self, tmp_path: Path):
        """Создание файла в несуществующей директории."""
        file = tmp_path / "deep" / "nested" / "dir" / "test.py"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file)

            assert result == f"file://{file.resolve()}"
            assert file.exists()
            assert file.parent.exists()

    def test_create_opens_existing_file(self, tmp_path: Path):
        """Если файл уже существует — открывается без ошибки."""
        file = tmp_path / "existing.py"
        file.write_text("# existing content")

        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file)

            # Файл открыт, а не перезаписан
            assert result == f"file://{file.resolve()}"
            assert file.read_text() == "# existing content"
            mock_open.assert_called_once()

    def test_create_refuses_to_overwrite_when_no_open(self, tmp_path: Path):
        """Если open_after_create=False и файл существует — падает с FileExistsError."""
        file = tmp_path / "existing.py"
        file.write_text("original")

        with pytest.raises(FileExistsError):
            create_test(file, open_after_create=False)

    def test_create_without_opening(self, tmp_path: Path):
        """Создание файла без автоматического открытия."""
        file = tmp_path / "no_open.py"
        
        result = create_test(file, open_after_create=False)

        assert result == f"file://{file.resolve()}"
        assert file.exists()

    def test_create_with_any_name(self, tmp_path: Path):
        """Создание файла с любым именем (не только test_...)."""
        # Имена, которые не начинаются с test_
        for filename in ["main.py", "utils.py", "README.md", "notes.txt"]:
            file = tmp_path / filename
            
            with patch("breaker.engine.executor.open_file") as mock_open:
                mock_open.return_value = f"file://{file.resolve()}"
                result = create_test(file)

                assert file.exists()
                assert result == f"file://{file.resolve()}"

    def test_create_with_python_template(self, tmp_path: Path):
        """Создание Python-файла с шаблоном 'python'."""
        file = tmp_path / "main.py"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, template="python")

            assert file.exists()
            content = file.read_text()
            assert "def main():" in content
            assert 'if __name__ == "__main__"' in content

    def test_create_with_markdown_template(self, tmp_path: Path):
        """Создание Markdown-файла с шаблоном 'markdown'."""
        file = tmp_path / "README.md"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, template="markdown")

            assert file.exists()
            content = file.read_text()
            assert "# Readme" in content
            assert "## Описание" in content

    def test_create_with_text_template(self, tmp_path: Path):
        """Создание текстового файла с шаблоном 'text'."""
        file = tmp_path / "notes.txt"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, template="text")

            assert file.exists()
            content = file.read_text()
            assert "Notes" in content

    def test_unknown_template_raises(self, tmp_path: Path):
        """Неизвестный шаблон — ValueError."""
        file = tmp_path / "test.py"
        with pytest.raises(ValueError):
            create_test(file, template="nonexistent_template")

    def test_empty_template(self, tmp_path: Path):
        """Шаблон 'empty' создаёт пустой файл."""
        file = tmp_path / "empty.txt"
        
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{file.resolve()}"
            result = create_test(file, template="empty")

            assert result == f"file://{file.resolve()}"
            assert file.exists()
            assert file.read_text() == ""


# Расширенные тесты execute_ritual()


class TestExecuteRitualExtended:
    """Расширенные тесты execute_ritual() для всех типов действий."""

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

    def test_execute_create_test_opens_existing(self, tmp_path: Path):
        """execute_ritual() с CREATE_TEST и существующим файлом — открывает его."""
        test_file = tmp_path / "existing.py"
        test_file.write_text("# existing")

        ritual = Ritual(
            signal="нет тестов",
            action="создать тест",
            target=str(test_file),
            action_type=ActionType.CREATE_TEST,
        )

        # Мокаем open_file, чтобы не запускать реальный редактор
        with patch("breaker.engine.executor.open_file") as mock_open:
            mock_open.return_value = f"file://{test_file.resolve()}"
            result = execute_ritual(ritual)

            assert isinstance(result, RitualResult)
            assert result.success is True  # ← Теперь успех!
            assert result.evidence_link == f"file://{test_file.resolve()}"
            # Файл не перезаписан
            assert test_file.read_text() == "# existing"
            # open_file был вызван
            mock_open.assert_called_once()
