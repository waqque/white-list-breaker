# Все тесты изолированы через tmp_path, чтобы не зависеть от реального файла.
import pytest
from unittest.mock import patch
from breaker.storage.templates import RuleTemplate, TemplateStorage
import breaker.ui.template_editor as editor_module


@pytest.fixture
def isolated_storage(tmp_path):
    # Создаём изолированное хранилище для каждого теста.
    storage = TemplateStorage(
        system_file="data/examples/default_templates.json",
        user_file=str(tmp_path / "test_templates.json"),
    )
    # Подменяем глобальный storage в модуле
    original_storage = editor_module.storage
    editor_module.storage = storage
    yield storage
    # Возвращаем оригинальный storage после теста
    editor_module.storage = original_storage


def test_list_templates_ui_with_data(isolated_storage, capsys):
    from breaker.ui.template_editor import list_templates_ui

    list_templates_ui()
    captured = capsys.readouterr()
    assert "Список сохранённых шаблонов" in captured.out


@patch(
    "rich.prompt.Prompt.ask",
    side_effect=[
        "Тестовый шаблон",
        "тест сигнал",
        "тест действие",
        "test.py",
        "тест описание",
        "1",
    ],
)
def test_create_template_ui(mock_input, isolated_storage, capsys):
    from breaker.ui.template_editor import create_template_ui

    initial_count = len(isolated_storage.list_templates())
    create_template_ui()
    final_count = len(isolated_storage.list_templates())
    assert final_count == initial_count + 1
    captured = capsys.readouterr()
    assert "создан" in captured.out


@patch("rich.prompt.Prompt.ask", return_value="user-999")
@patch("rich.prompt.Confirm.ask", return_value=True)
def test_delete_template_ui_user_template(mock_confirm, mock_input, isolated_storage, capsys):
    from breaker.ui.template_editor import delete_template_ui

    test_template = RuleTemplate(
        id="user-999",
        name="Тест",
        signal="сигнал",
        action="действие",
        target="target.py",
        action_type="open_file",
        is_system=False,
    )
    isolated_storage.save_template(test_template)

    delete_template_ui()
    captured = capsys.readouterr()
    assert "удалён" in captured.out


@patch("rich.prompt.Prompt.ask", return_value="run_linter")
def test_delete_template_ui_system_template(mock_input, isolated_storage, capsys):
    from breaker.ui.template_editor import delete_template_ui

    delete_template_ui()
    captured = capsys.readouterr()
    assert "нельзя удалить" in captured.out.lower()


@patch("rich.prompt.Prompt.ask", return_value="файл")
def test_search_templates_ui(mock_input, isolated_storage, capsys):
    from breaker.ui.template_editor import search_templates_ui

    search_templates_ui()
    captured = capsys.readouterr()
    assert "Результаты поиска" in captured.out


@patch("rich.prompt.Prompt.ask", return_value="несуществующий_запрос_xyz")
def test_search_templates_ui_no_results(mock_input, isolated_storage, capsys):
    from breaker.ui.template_editor import search_templates_ui

    search_templates_ui()
    captured = capsys.readouterr()
    assert "ничего не найдено" in captured.out.lower()
