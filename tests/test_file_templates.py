from pathlib import Path
from breaker.engine.file_templates import FileTemplates

# Python-шаблоны

def test_python_module_template():
    """Шаблон модуля по умолчанию."""
    result = FileTemplates.get_template(Path("classes.py"), "default")
    assert result is not None
    assert "Module: classes" in result
    assert "TODO" in result


def test_python_function_template():
    """Шаблон функции."""
    result = FileTemplates.get_template(Path("utils.py"), "function")
    assert result is not None
    assert "def utils" in result
    assert "TODO" in result


def test_python_class_template():
    """Шаблон класса."""
    result = FileTemplates.get_template(Path("classes.py"), "class")
    assert result is not None
    assert "class Classes" in result
    assert "def __init__" in result


def test_python_test_template():
    """Шаблон теста."""
    result = FileTemplates.get_template(Path("test_main.py"), "test")
    assert result is not None
    assert "Tests for main" in result
    assert "def test_placeholder" in result


def test_python_test_file_auto_detected():
    """Тестовый файл автоматически получает тестовый шаблон."""
    result = FileTemplates.get_template(Path("test_classes.py"), "default")
    assert result is not None
    assert "def test_placeholder" in result


def test_python_class_name_pascal_case():
    """Имя класса генерируется"""
    result = FileTemplates.get_template(Path("my_cool_class.py"), "class")
    assert "class MyCoolClass" in result


# Markdown-шаблон

def test_markdown_template():
    """Шаблон Markdown."""
    result = FileTemplates.get_template(Path("README.md"))
    assert result is not None
    assert "# Readme" in result
    assert "## Описание" in result


# JSON-шаблон

def test_json_template():
    """Шаблон JSON."""
    result = FileTemplates.get_template(Path("config.json"))
    assert result is not None
    assert '"name": "config"' in result
    assert '"version"' in result

# YAML-шаблон

def test_yaml_template():
    """Шаблон YAML."""
    result = FileTemplates.get_template(Path("settings.yaml"))
    assert result is not None
    assert "name: settings" in result
    assert "version:" in result


def test_yml_extension():
    """Расширение .yml тоже работает."""
    result = FileTemplates.get_template(Path("config.yml"))
    assert result is not None
    assert "name: config" in result

# Text-шаблон

def test_text_template():
    """Шаблон текста."""
    result = FileTemplates.get_template(Path("notes.txt"))
    assert result is not None
    assert "Notes" in result
    assert "TODO" in result

# Граничные случаи

def test_unknown_extension():
    """Неизвестное расширение возвращает None."""
    result = FileTemplates.get_template(Path("file.xyz"))
    assert result is None


def test_supported_extensions():
    """Список поддерживаемых расширений."""
    exts = FileTemplates.supported_extensions()
    assert ".py" in exts
    assert ".md" in exts
    assert ".json" in exts
    assert ".yaml" in exts
    assert ".txt" in exts


def test_python_template_types():
    """Список типов шаблонов для Python."""
    types = FileTemplates.python_template_types()
    assert "function" in types
    assert "class" in types
    assert "test" in types
    assert "module" in types