"""Генератор шаблонов содержимого для разных типов файлов.

Используется модулем help_menu.py для вставки заготовок в файлы
при бездействии пользователя.
"""

from pathlib import Path
from typing import Optional


class FileTemplates:
    """Генератор шаблонов содержимого для разных типов файлов."""

    # Публичный API

    @staticmethod
    def get_template(file_path: Path, template_type: str = "default") -> Optional[str]:
        """Получить шаблон для файла по его расширению и типу.

        Args:
            file_path: Путь к файлу (расширение определяет базовый шаблон).
            template_type: Тип шаблона:
                - Для .py: "function", "class", "test", "module", "default"
                - Для .md: "default" (единственный вариант)
                - Для .json: "default"
                - Для .yaml/.yml: "default"
                - Для .txt: "default"

        Returns:
            str: Содержимое шаблона или None, если тип не поддерживается.
        """
        suffix = file_path.suffix.lower()

        # Python — поддерживает несколько типов шаблонов
        if suffix == ".py":
            return FileTemplates._get_python_template(file_path, template_type)

        # Остальные типы — один шаблон на расширение
        templates = {
            ".md": FileTemplates._markdown_template,
            ".json": FileTemplates._json_template,
            ".yaml": FileTemplates._yaml_template,
            ".yml": FileTemplates._yaml_template,
            ".txt": FileTemplates._text_template,
        }

        generator = templates.get(suffix)
        if generator is None:
            return None

        return generator(file_path)

    @staticmethod
    def supported_extensions() -> list[str]:
        """Вернуть список поддерживаемых расширений."""
        return [".py", ".md", ".json", ".yaml", ".yml", ".txt"]

    @staticmethod
    def python_template_types() -> list[str]:
        """Вернуть список доступных типов шаблонов для Python."""
        return ["function", "class", "test", "module", "default"]

    # Python-шаблоны

    @staticmethod
    def _get_python_template(file_path: Path, template_type: str) -> str:
        """Выбрать Python-шаблон по типу."""
        # Тестовый файл — всегда возвращаем тестовый шаблон
        if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
            return FileTemplates._python_test_template(file_path)

        # Явный выбор типа
        type_map = {
            "function": FileTemplates._python_function_template,
            "class": FileTemplates._python_class_template,
            "test": FileTemplates._python_test_template,
            "module": FileTemplates._python_module_template,
            "default": FileTemplates._python_module_template,
        }

        generator = type_map.get(template_type, FileTemplates._python_module_template)
        return generator(file_path)

    @staticmethod
    def _python_module_template(file_path: Path) -> str:
        """Базовый шаблон Python-модуля."""
        module_name = file_path.stem
        return f'''"""Module: {module_name}.

TODO: add module description.
"""


# TODO: add your code here
'''

    @staticmethod
    def _python_function_template(file_path: Path) -> str:
        """Шаблон Python-функции."""
        module_name = file_path.stem
        # Генерируем имя функции из имени файла
        func_name = module_name if module_name != "main" else "my_function"
        # Убираем невалидные символы
        func_name = "".join(c if c.isalnum() or c == "_" else "_" for c in func_name)
        if func_name and func_name[0].isdigit():
            func_name = f"func_{func_name}"

        return f'''"""Module: {module_name}."""


def {func_name}():
    """TODO: add function description.

    Returns:
        TODO: describe return value.
    """
    # TODO: implement
    pass
'''

    @staticmethod
    def _python_class_template(file_path: Path) -> str:
        """Шаблон Python-класса."""
        module_name = file_path.stem
        # Генерируем имя класса 
        class_name = "".join(
            word.capitalize() for word in module_name.replace("-", "_").split("_")
        )
        if not class_name:
            class_name = "MyClass"
        # Если начинается с цифры — добавляем префикс
        if class_name[0].isdigit():
            class_name = f"Class{class_name}"

        return f'''"""Module: {module_name}."""


class {class_name}:
    """TODO: add class description."""

    def __init__(self):
        """Initialize {class_name}."""
        # TODO: add attributes
        pass

    def __str__(self) -> str:
        """Return string representation."""
        return f"{class_name}()"

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return self.__str__()
'''

    @staticmethod
    def _python_test_template(file_path: Path) -> str:
        """Шаблон pytest-теста."""
        # Извлекаем имя модуля, который тестируем
        module_name = file_path.stem
        if module_name.startswith("test_"):
            module_name = module_name[5:]
        elif module_name.endswith("_test"):
            module_name = module_name[:-5]

        return f'''"""Tests for {module_name}."""

import pytest


def test_placeholder():
    """TODO: replace with real tests."""
    # Arrange
    expected = True

    # Act
    result = True

    # Assert
    assert result == expected


def test_another_case():
    """TODO: add another test case."""
    assert True is True
'''

    # Markdown-шаблон

    @staticmethod
    def _markdown_template(file_path: Path) -> str:
        """Шаблон Markdown-документа."""
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        return f"""# {title}

## Описание

TODO: добавить описание

## Использование

TODO: добавить примеры использования

## Примеры
TODO: добавить примеры кода

## Заметки

-
"""

    # JSON-шаблон

    @staticmethod
    def _json_template(file_path: Path) -> str:
        """Шаблон JSON-файла."""
        name = file_path.stem
        return f"""{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "TODO: add description",
  "settings": {{
    "debug": false,
    "log_level": "info"
  }}
}}
"""

    # YAML-шаблон
    @staticmethod
    def _yaml_template(file_path: Path) -> str:
        """Шаблон YAML-файла."""
        name = file_path.stem
        return f"""# {name}
name: {name}
version: "1.0.0"
description: "TODO: add description"

settings:
  debug: false
  log_level: info
"""

    # Text-шаблон
    @staticmethod
    def _text_template(file_path: Path) -> str:
        """Шаблон текстового файла."""
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        return f"""{title}
{"=" * len(title)}

TODO: add content here

"""