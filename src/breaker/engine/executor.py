"""Executor — исполнение микро-шагов на основе правила "если-то".

Этот модуль получает объект Ritual из core/schema.py, выполняет действие
в зависимости от action_type, и возвращает RitualResult.

Поддерживает три типа действий:
- OPEN_FILE: открыть файл в редакторе (кроссплатформенно)
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
        raise BreakerFileNotFoundError(f"Указан путь к директории, а не к файлу: {path}")

    # Если указан конкретный редактор — пробуем его
    if editor:
        try:
            return _open_in_editor(path, editor, timeout)
        except CommandNotFoundError:
            # Fallback: если редактор не найден, используем системное приложение
            print(
                f"  Редактор '{editor}' не найден в PATH. "
                f"Открываю системным приложением по умолчанию..."
            )
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
        raise CommandNotFoundError(f"Editor '{editor}' not found. Install it or check PATH.")
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError(f"Editor '{editor}' did not start within {timeout} seconds.")


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
            raise CommandNotFoundError(f"Unsupported OS: {system}. Cannot open file automatically.")
    except FileNotFoundError:
        raise CommandNotFoundError(
            f"System opener not found on {system}. "
            "Try specifying an editor explicitly (e.g., editor='code')."
        )
    except subprocess.TimeoutExpired:
        raise CommandTimeoutError("System opener timed out.")
    except subprocess.CalledProcessError as e:
        raise CommandFailedError(e.returncode, str(e.stderr))

def create_test(
    path: str | Path,
    content: str = "",
    template: str = "auto",  
    open_after_create: bool = True,
) -> str:
    """
    Создаёт файл (любой, не только тест) с опциональным шаблоном и открывает его.

    Args:
        path: Путь, куда создать файл (с любым именем).
        content: Содержимое файла. Если пусто — используется шаблон.
        template: Шаблон содержимого. Если "auto" — определяется по расширению.
                  Доступные: 'pytest', 'unittest', 'python', 'markdown',
                  'json', 'yaml', 'text', 'empty'.
        open_after_create: Если True (по умолчанию), файл автоматически
                          открывается в редакторе после создания.

    Returns:
        str: URI файла (file:///path/to/file) для evidence_link в xAPI.
    """
    path = Path(path).resolve()

    # Если файл уже существует — просто открываем его
    if path.exists():
        if open_after_create:
            print(f"  Файл уже существует, открываю: {path}")
            return open_file(path)
        else:
            raise FileExistsError(f"File already exists: {path}")

    # Автоопределение шаблона по расширению
    if template == "auto":
        template = _detect_template_by_extension(path)
        print(f"  Автоопределение шаблона: {template}")

    # Если контент не задан — берём из шаблона
    if not content:
        content = _get_template(template, path.stem)

    # Создаём родительские директории, если их нет
    path.parent.mkdir(parents=True, exist_ok=True)

    # Записываем файл
    path.write_text(content, encoding="utf-8")
    print(f"  Файл создан: {path}")

    # Открываем файл после создания
    if open_after_create:
        return open_file(path)

    return f"file://{path}"


def _detect_template_by_extension(path: Path) -> str:
    """Определить шаблон по расширению файла.
    """
    suffix = path.suffix.lower()
    name = path.name.lower()

    # Тестовые файлы — всегда pytest
    if name.startswith("test_") or name.endswith("_test.py"):
        return "pytest"

    # По расширению
    extension_map = {
        ".py": "python",
        ".md": "markdown",
        ".json": "empty",     
        ".yaml": "empty",     
        ".yml": "empty",      
        ".txt": "text",
    }

    return extension_map.get(suffix, "empty")


def _get_template(template: str, module_name: str) -> str:
    """Возвращает содержимое шаблона по имени."""
    templates = {
        # Шаблоны для тестов
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
        # Шаблоны для обычных файлов
        "python": f'''"""Module: {module_name}.

TODO: add module description.
"""


def main():
    """Entry point."""
    pass


if __name__ == "__main__":
    main()
''',
        "markdown": f'''# {module_name.replace("_", " ").title()}

## Описание

TODO: добавить описание.

## Использование

TODO: добавить примеры использования.

## Заметки

- 
''',
        "text": f'''{module_name.replace("_", " ").title()}
{"=" * len(module_name)}

TODO: добавить содержимое.
''',
        "empty": "",
    }

    if template not in templates:
        raise ValueError(
            f"Unknown template: {template}. "
            f"Available: {list(templates.keys())}"
        )

    return templates[template]