from unittest.mock import patch
from breaker.storage.templates import RuleTemplate
from breaker.ui.template_editor import (
    storage,
    list_templates_ui,
    create_template_ui,
    delete_template_ui,
    search_templates_ui,
)


def test_list_templates_ui_with_data(capsys):
    # Показываем список с шаблонами.
    list_templates_ui()
    captured = capsys.readouterr()
    assert "Список сохранённых шаблонов" in captured.out


@patch('rich.prompt.Prompt.ask', side_effect=[
    'Тестовый шаблон',
    'тест сигнал',
    'тест действие',
    'test.py',
    'тест описание',
    '1',
])
def test_create_template_ui(mock_input, capsys):
    # Создаём шаблон через UI.
    initial_count = len(storage.list_templates())
    create_template_ui()
    final_count = len(storage.list_templates())
    assert final_count == initial_count + 1
    captured = capsys.readouterr()
    assert "создан" in captured.out


@patch('rich.prompt.Prompt.ask', return_value='user-999')
@patch('rich.prompt.Confirm.ask', return_value=True)
def test_delete_template_ui_user_template(mock_confirm, mock_input, capsys):
    # Удаляем пользовательский шаблон.
    test_template = RuleTemplate(
        id="user-999",
        name="Тест",
        signal="сигнал",
        action="действие",
        target="target.py",
        action_type="open_file",
        is_system=False,
    )
    storage.save_template(test_template)

    delete_template_ui()
    captured = capsys.readouterr()
    assert "удалён" in captured.out


@patch('rich.prompt.Prompt.ask', return_value='run_linter')
def test_delete_template_ui_system_template(mock_input, capsys):
    # Пытаемся удалить системный шаблон — должна быть ошибка.
    delete_template_ui()
    captured = capsys.readouterr()
    assert "нельзя удалить" in captured.out.lower()


@patch('rich.prompt.Prompt.ask', return_value='файл')
def test_search_templates_ui(mock_input, capsys):
    # Ищем шаблоны по запросу.
    search_templates_ui()
    captured = capsys.readouterr()
    assert "Результаты поиска" in captured.out


@patch('rich.prompt.Prompt.ask', return_value='несуществующий_запрос_xyz')
def test_search_templates_ui_no_results(mock_input, capsys):
    # Ищем по несуществующему запросу.
    search_templates_ui()
    captured = capsys.readouterr()
    assert "ничего не найдено" in captured.out.lower()