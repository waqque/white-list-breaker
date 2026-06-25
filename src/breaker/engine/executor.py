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
    editor: Optional[str] = None,
    timeout: int = 10,
) -> str:
    """
    Кроссплатформенно открывает существующий файл в редакторе или системном приложении.
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
    
    # Если указан конкретный редактор — запускаем его
    if editor:
        return _open_in_editor(path, editor, timeout)
    
    # Иначе — открываем системным приложением по умолчанию
    return _open_system_default(path)


def _open_in_editor(path: Path, editor: str, timeout: int) -> str:
    """Открывает файл в указанном редакторе (code, vim, nano и т.д.)."""
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


# Заглушки для функций, которые будут реализованы позже
def run_shell(command: str, timeout: int = 30) -> str:

    raise NotImplementedError("run_shell() will be implemented later")


def create_test(path: str | Path, template: str = "pytest") -> str:
    raise NotImplementedError("create_test() will be implemented later")