from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from breaker.ui.help_menu import (
    _get_file_type,
    _is_test_file,
    _get_max_choice_level1,
    show_help_level1,
    show_help_level2,
    apply_help_choice,
    _insert_template,
    _insert_text,
    show_success_message,
)


def test_get_file_type_python():
    assert _get_file_type(Path("main.py")) == "python"


def test_get_file_type_markdown():
    assert _get_file_type(Path("README.md")) == "markdown"


def test_get_file_type_json():
    assert _get_file_type(Path("config.json")) == "json"


def test_get_file_type_yaml():
    assert _get_file_type(Path("settings.yaml")) == "yaml"


def test_get_file_type_yml():
    assert _get_file_type(Path("settings.yml")) == "yaml"


def test_get_file_type_text():
    assert _get_file_type(Path("notes.txt")) == "text"


def test_get_file_type_unknown():
    assert _get_file_type(Path("file.xyz")) == "other"


def test_is_test_file_true():
    assert _is_test_file(Path("test_main.py")) is True
    assert _is_test_file(Path("main_test.py")) is True


def test_is_test_file_false():
    assert _is_test_file(Path("main.py")) is False
    assert _is_test_file(Path("utils.py")) is False


def test_max_choice_python_regular():
    assert _get_max_choice_level1("python", False) == 5


def test_max_choice_python_test():
    assert _get_max_choice_level1("python", True) == 4


def test_max_choice_markdown():
    assert _get_max_choice_level1("markdown", False) == 4


def test_max_choice_json():
    assert _get_max_choice_level1("json", False) == 3


def test_max_choice_yaml():
    assert _get_max_choice_level1("yaml", False) == 3


def test_max_choice_other():
    assert _get_max_choice_level1("other", False) == 2


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=5)
def test_show_help_level1_python_regular(mock_ask):
    result = show_help_level1(Path("classes.py"))
    assert result == 5


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=1)
def test_show_help_level1_python_test(mock_ask):
    result = show_help_level1(Path("test_main.py"))
    assert result == 1


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=3)
def test_show_help_level1_markdown(mock_ask):
    result = show_help_level1(Path("README.md"))
    assert result == 3


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=2)
def test_show_help_level1_json(mock_ask):
    result = show_help_level1(Path("config.json"))
    assert result == 2


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=1)
def test_show_help_level1_other(mock_ask):
    result = show_help_level1(Path("file.xyz"))
    assert result == 1


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=6)
def test_show_help_level2_default(mock_ask):
    result = show_help_level2(Path("main.py"))
    assert result == 6


@patch("breaker.ui.help_menu.IntPrompt.ask", return_value=3)
def test_show_help_level2_assert(mock_ask):
    result = show_help_level2(Path("main.py"))
    assert result == 3


def test_apply_level1_python_function(tmp_path):
    file = tmp_path / "utils.py"
    file.write_text("")
    with patch("breaker.ui.help_menu._insert_template", return_value="template:function"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:function"


def test_apply_level1_python_class(tmp_path):
    file = tmp_path / "classes.py"
    file.write_text("")
    with patch("breaker.ui.help_menu._insert_template", return_value="template:class"):
        result = apply_help_choice(2, file, level=1)
    assert result == "template:class"


def test_apply_level1_python_test(tmp_path):
    file = tmp_path / "test_main.py"
    file.write_text("")
    with patch("breaker.ui.help_menu._insert_template", return_value="template:test"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:test"


def test_apply_level1_python_todo(tmp_path):
    file = tmp_path / "main.py"
    file.write_text("")
    with patch("breaker.ui.help_menu._insert_text", return_value="text_inserted"):
        result = apply_help_choice(3, file, level=1)
    assert result == "text_inserted"


def test_apply_level1_python_timer():
    result = apply_help_choice(4, Path("main.py"), level=1)
    assert result == "timer"


def test_apply_level1_python_skip():
    result = apply_help_choice(5, Path("main.py"), level=1)
    assert result == "skip"


def test_apply_level1_markdown_template(tmp_path):
    file = tmp_path / "README.md"
    with patch("breaker.ui.help_menu._insert_template", return_value="template:default"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:default"


def test_apply_level1_markdown_heading(tmp_path):
    file = tmp_path / "README.md"
    with patch("breaker.ui.help_menu._insert_text", return_value="text_inserted"):
        result = apply_help_choice(2, file, level=1)
    assert result == "text_inserted"


def test_apply_level1_json_template(tmp_path):
    file = tmp_path / "config.json"
    with patch("breaker.ui.help_menu._insert_template", return_value="template:default"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:default"


def test_apply_level1_yaml_template(tmp_path):
    file = tmp_path / "settings.yaml"
    with patch("breaker.ui.help_menu._insert_template", return_value="template:default"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:default"


def test_apply_level2_todo(tmp_path):
    file = tmp_path / "main.py"
    with patch("breaker.ui.help_menu._insert_text", return_value="text_inserted"):
        result = apply_help_choice(1, file, level=2)
    assert result == "text_inserted"


def test_apply_level2_pass(tmp_path):
    file = tmp_path / "main.py"
    with patch("breaker.ui.help_menu._insert_text", return_value="text_inserted"):
        result = apply_help_choice(2, file, level=2)
    assert result == "text_inserted"


def test_apply_level2_assert(tmp_path):
    file = tmp_path / "main.py"
    with patch("breaker.ui.help_menu._insert_text", return_value="text_inserted"):
        result = apply_help_choice(3, file, level=2)
    assert result == "text_inserted"


def test_apply_level2_open_readme(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Test")
    result = apply_help_choice(4, Path("main.py"), level=2)
    assert result.startswith("open:")


def test_apply_level2_open_readme_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = apply_help_choice(4, Path("main.py"), level=2)
    assert result == "skip"


def test_apply_level2_timer():
    result = apply_help_choice(5, Path("main.py"), level=2)
    assert result == "timer"


def test_apply_level2_skip():
    result = apply_help_choice(6, Path("main.py"), level=2)
    assert result == "skip"


def test_insert_template_into_empty_file(tmp_path):
    file = tmp_path / "utils.py"
    file.write_text("")
    with patch("breaker.engine.file_templates.FileTemplates.get_template", return_value="def utils():\n    pass"):
        result = _insert_template(file, "function")
    assert result == "template:function"
    assert "def utils" in file.read_text()


def test_insert_template_into_nonempty_file(tmp_path):
    file = tmp_path / "utils.py"
    file.write_text("# existing code\n")
    with patch("breaker.engine.file_templates.FileTemplates.get_template", return_value="def utils():\n    pass"):
        result = _insert_template(file, "function")
    assert result == "template:function"
    content = file.read_text()
    assert "# existing code" in content
    assert "def utils" in content


def test_insert_template_creates_file(tmp_path):
    file = tmp_path / "new.py"
    assert not file.exists()
    with patch("breaker.engine.file_templates.FileTemplates.get_template", return_value="class New:\n    pass"):
        result = _insert_template(file, "class")
    assert result == "template:class"
    assert file.exists()


def test_insert_template_unknown_type(tmp_path):
    file = tmp_path / "file.xyz"
    with patch("breaker.engine.file_templates.FileTemplates.get_template", return_value=None):
        result = _insert_template(file, "default")
    assert result == "skip"


def test_insert_text_into_existing_file(tmp_path):
    file = tmp_path / "main.py"
    file.write_text("# start\n")
    result = _insert_text(file, "# end\n")
    assert result == "text_inserted"
    assert file.read_text() == "# start\n# end\n"


def test_insert_text_creates_file(tmp_path):
    file = tmp_path / "new.txt"
    result = _insert_text(file, "hello\n")
    assert result == "text_inserted"
    assert file.read_text() == "hello\n"


def test_show_success_message(capsys):
    show_success_message(Path("main.py"), {"total_chars_added": 150})
    captured = capsys.readouterr()
    assert "Отлично" in captured.out
    assert "main.py" in captured.out


def test_apply_help_choice_delegates_level1(tmp_path):
    """apply_help_choice() - делегирует в _apply_level1_choice."""
    file = tmp_path / "main.py"
    with patch("breaker.ui.help_menu._apply_level1_choice", return_value="template:function"):
        result = apply_help_choice(1, file, level=1)
    assert result == "template:function"


def test_apply_help_choice_delegates_level2(tmp_path):
    """apply_help_choice() - делегирует в _apply_level2_choice."""
    file = tmp_path / "main.py"
    with patch("breaker.ui.help_menu._apply_level2_choice", return_value="text_inserted"):
        result = apply_help_choice(1, file, level=2)
    assert result == "text_inserted"