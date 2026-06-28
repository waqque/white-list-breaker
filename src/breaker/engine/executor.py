"""Executor — исполнение микро-шагов на основе правила "если-то".

Этот модуль получает объект Ritual из core/schema.py, выполняет действие
в зависимости от action_type, и возвращает RitualResult.

Поддерживает три типа действий:
- OPEN_FILE: открыть файл в редакторе (кроссплатформенно)
- RUN_SHELL: выполнить команду в shell
- CREATE_TEST: создать файл-шаблон теста
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from breaker.core.schema import Ritual, RitualResult, ActionType
from .exceptions import (
    BreakerFileNotFoundError,
    CommandNotFoundError,
    CommandTimeoutError,
    CommandFailedError,
)


def execute_ritual(ritual: Ritual) -> RitualResult:
    """
    Возвращает RitualResult с результатом (успех/ошибка)
    """

    print(f"\n Выполняю: {ritual.format_rule()}")
    print(f"   Тип действия: {ritual.action_type.value}")
    print(f"   Цель: {ritual.target}")

    try:
        # Выбираем стратегию выполнения на основе action_type
        if ritual.action_type == ActionType.OPEN_FILE:
            evidence = open_file(ritual.target)
        elif ritual.action_type == ActionType.RUN_SHELL:
            evidence = run_shell(ritual.target)
        elif ritual.action_type == ActionType.CREATE_TEST:
            evidence = create_test(ritual.target)
        else:
            raise ValueError(f"Неизвестный тип действия: {ritual.action_type}")

        # Создаём успешный результат
        result = RitualResult(
            ritual=ritual,
            success=True,
            evidence_link=evidence,
        )
        result.mark_finished()
        print(f" Действие выполнено успешно")
        print(f"   Evidence: {evidence}")
        return result

    except Exception as e:
        # Создаём результат с ошибкой
        result = RitualResult(
            ritual=ritual,
            success=False,
            error_message=str(e),
        )
        result.mark_finished()
        print(f" Ошибка выполнения: {e}")
        return result


def open_file(
    path: str | Path,
    editor: Optional[str] = "code",
    timeout: int = 10,
) -> str:
    """
    Кроссплатформенно открывает существующий файл в редакторе или системном приложении.
    
    Если указанный редактор не найден в PATH — автоматически использует
    системное приложение по умолчанию (fallback).
    """
    # Проверка на пустой путь
    if not path or str(path).strip() == "":
        raise ValueError("Path cannot be empty")
    
    path = Path(path).resolve()
  
    if not path.exists():
        raise BreakerFileNotFoundError(
            f"Файл не найден: {path}\n"
            f"Модуль открывает только существующие файлы. "
            f"Создайте файл вручную или используйте create_test()."
        )
    
    # Если файл — директория, тоже ошибка
    if path.is_dir():
        raise BreakerFileNotFoundError(
            f"Указан путь к директории, а не к файлу: {path}"
        )
    
    # Если указан конкретный редактор — пробуем его
    if editor:
        try:
            return _open_in_editor(path, editor, timeout)
        except CommandNotFoundError:
            # Fallback: если редактор не найден, используем системное приложение
            print(f"  Редактор '{editor}' не найден в PATH. "
                  f"Открываю системным приложением по умолчанию...")
            return _open_system_default(path)
    
    # Иначе — открываем системным приложением по умолчанию
    return _open_system_default(path)


def _open_in_editor(path: Path, editor: str, timeout: int) -> str:
    """Открывает файл в редакторе"""
    try:
        cmd = [editor, str(path)]
        subprocess.run(
            cmd,
            timeout=timeout,
            check=False,
            capture_output=True,
        )
        return f"file://{path}"
    except FileNotFoundError:
        raise CommandNotFoundError(
            f"Editor '{editor}' not found. Install it or check PATH."
        )
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError(
            f"Editor '{editor}' did not start within {timeout} seconds."
        )

def _open_system_default(path: Path) -> str:
    """Открывает файл системным приложением по умолчанию."""
    system = platform.system()

    try:
        if system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
            return f"file://{path}"
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(path)], check=True, timeout=10)
            return f"file://{path}"
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path)], check=True, timeout=10)
            return f"file://{path}"
        else:
            raise CommandNotFoundError(
                f"Unsupported OS: {system}. Cannot open file automatically."
            )
    except FileNotFoundError:
        raise CommandNotFoundError(
            f"System opener not found on {system}. "
            "Try specifying an editor explicitly (e.g., editor='code')."
        )
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError("System opener timed out.")
    except subprocess.CalledProcessError as e:
        raise CommandFailedError(e.returncode, str(e.stderr))


def run_shell(
    command: str,
    cwd: Optional[str | Path] = None,
    timeout: int = 30,
    capture_output: bool = True,
) -> str:
    """
    Запускает shell-команду с обработкой ошибок и таймаутом.

    """
    # Проверка на пустую команду
    if not command or str(command).strip() == "":
        raise ValueError("Command cannot be empty")
    
    # Проверка на опасные команды 
    dangerous_commands = ["rm -rf /", "format c:", "del /f /s /q"]
    if any(dangerous in command.lower() for dangerous in dangerous_commands):
        raise ValueError(f"Dangerous command detected: {command}")
    
    print(f"   Выполняю команду: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
        )

        # Если команда вернула ненулевой код — считаем это ошибкой
        if result.returncode != 0:
            raise CommandFailedError(result.returncode, result.stderr or "")

        print(f"   Команда выполнена успешно (код: {result.returncode})")
        return f"shell://{command}"

    except FileNotFoundError:
        raise CommandNotFoundError(f"Shell or command not found: {command}")
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError(
            f"Command '{command}' timed out after {timeout} seconds."
        )


def create_test(
    path: str | Path,
    content: str = "",
    template: str = "pytest",
) -> str:
    """
    Создаёт файл теста (или любой другой файл) с опциональным шаблоном.

    """
    path = Path(path).resolve()

    # Если контент не задан — берём из шаблона
    if not content:
        content = _get_template(template, path.stem)

    # Создаём родительские директории, если их нет
    path.parent.mkdir(parents=True, exist_ok=True)

    # Записываем файл (не перезаписываем, если уже существует — safety)
    if path.exists():
        raise FileExistsError(f"File already exists: {path}")

    path.write_text(content, encoding="utf-8")
    print(f"  Файл создан: {path}")
    return f"file://{path}"


def _get_template(template: str, module_name: str) -> str:
    """Возвращает содержимое шаблона по имени."""
    templates = {
        "pytest": f'''"""Tests for {module_name}."""


def test_placeholder():
    """TODO: replace with real tests."""
    assert True
''',
        "unittest": f'''"""Tests for {module_name}."""
import unittest


class Test{module_name.title().replace("_", "")}(unittest.TestCase):
    """TODO: replace with real tests."""

    def test_placeholder(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
''',
        "empty": "",
    }

    if template not in templates:
        raise ValueError(
            f"Unknown template: {template}. Available: {list(templates.keys())}"
        )

    return templates[template]