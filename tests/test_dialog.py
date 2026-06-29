from unittest.mock import patch
from breaker.core.schema import Ritual, ActionType
from breaker.ui.dialog import (
    ask_signal,
    ask_action,
    ask_file_mode,
    ask_target,
    detect_action_type,
    ask_ritual,
    confirm_rule,
)


@patch("rich.prompt.Prompt.ask", return_value="файл пуст")
def test_ask_signal(mock_input):
    # Проверяем, что ask_signal возвращает введённую строку.
    result = ask_signal()
    assert result == "файл пуст"


@patch("rich.prompt.Prompt.ask", return_value="напишу функцию")
def test_ask_action(mock_input):
    # Проверяем, что ask_action возвращает введённую строку.
    result = ask_action()
    assert result == "напишу функцию"

@patch("rich.prompt.Prompt.ask", return_value="1")
def test_ask_file_mode_create(mock_input):
    # Проверяем, что ask_file_mode возвращает "create" при выборе 1.
    result = ask_file_mode()
    assert result == "create"


@patch("rich.prompt.Prompt.ask", return_value="2")
def test_ask_file_mode_open(mock_input):
    # Проверяем, что ask_file_mode возвращает "open" при выборе 2.
    result = ask_file_mode()
    assert result == "open"


@patch("rich.prompt.Prompt.ask", return_value="main.py")
@patch("pathlib.Path.exists", return_value=False)
def test_ask_target(mock_exists, mock_input):
    # Проверяем, что ask_target возвращает введённую строку.
    result = ask_target("create")
    assert result == "main.py"


def test_detect_action_type_open_file():
    # Тест определения типа действия: открытие файла (режим "open").
    assert detect_action_type("main.py", "open") == ActionType.OPEN_FILE
    assert detect_action_type("src/app.js", "open") == ActionType.OPEN_FILE
    assert detect_action_type("example.py", "open") == ActionType.OPEN_FILE


def test_detect_action_type_create_test():
    # Тест определения типа действия: создание файла (режим "create").
    assert detect_action_type("main.py", "create") == ActionType.CREATE_TEST
    assert detect_action_type("classes.py", "create") == ActionType.CREATE_TEST
    assert detect_action_type("README.md", "create") == ActionType.CREATE_TEST



def test_detect_action_type_test_file_in_open_mode():
    # Тест определения типа действия: тестовый файл в режиме "open".
    assert detect_action_type("tests/test_main.py", "open") == ActionType.CREATE_TEST
    assert detect_action_type("test_app.js", "open") == ActionType.CREATE_TEST
    assert detect_action_type("my_test.py", "open") == ActionType.CREATE_TEST


@patch("rich.prompt.Prompt.ask", side_effect=["файл пуст", "напишу функцию", "1", "main.py"])
@patch("pathlib.Path.exists", return_value=False)
def test_ask_ritual(mock_exists, mock_input):
    # Проверяем, что ask_ritual возвращает объект Ritual (4 вопроса).
    ritual = ask_ritual(task_id="test-task")
    assert isinstance(ritual, Ritual)
    assert ritual.signal == "файл пуст"
    assert ritual.action == "напишу функцию"
    assert ritual.target == "main.py"
    assert ritual.action_type == ActionType.CREATE_TEST  # режим "create"
    assert ritual.task_id == "test-task"


@patch("rich.prompt.Prompt.ask", side_effect=["консоль не запущена", "запущу npm", "2", "main.py"])
@patch("pathlib.Path.exists", return_value=True)
def test_ask_ritual_open_mode(mock_exists, mock_input):
    # Проверяем, что ask_ritual в режиме "open" использует OPEN_FILE.
    ritual = ask_ritual()
    assert ritual.action_type == ActionType.OPEN_FILE


@patch("rich.prompt.Prompt.ask", side_effect=["нужен тест", "создам тест", "1", "tests/test_main.py"])
@patch("pathlib.Path.exists", return_value=False)
def test_ask_ritual_create_test(mock_exists, mock_input):
    # Проверяем, что ask_ritual определяет создание теста.
    ritual = ask_ritual()
    assert ritual.action_type == ActionType.CREATE_TEST


@patch("rich.prompt.Confirm.ask", return_value=True)
def test_confirm_rule_positive(mock_confirm):
    # Пользователь подтверждает правило.
    ritual = Ritual(
        signal="файл пуст",
        action="напишу функцию",
        target="main.py",
        action_type=ActionType.OPEN_FILE,
    )
    result = confirm_rule(ritual)
    assert result is True


@patch("rich.prompt.Confirm.ask", return_value=False)
def test_confirm_rule_negative(mock_confirm):
    # Пользователь отклоняет правило.
    ritual = Ritual(
        signal="файл пуст",
        action="напишу функцию",
        target="main.py",
        action_type=ActionType.OPEN_FILE,
    )
    result = confirm_rule(ritual)
    assert result is False

@patch("rich.prompt.IntPrompt.ask", return_value=0)
def test_main_menu_exit(mock_input, capsys):
    """Главное меню - выход по пункту 0."""
    from breaker.ui.dialog import main_menu
    main_menu()
    captured = capsys.readouterr()
    assert "До свидания" in captured.out


@patch("rich.prompt.IntPrompt.ask", side_effect=KeyboardInterrupt)
def test_main_menu_ctrl_c(mock_input, capsys):
    """Главное меню - обработка Ctrl+C."""
    from breaker.ui.dialog import main_menu
    main_menu()
    captured = capsys.readouterr()
    assert "Выход" in captured.out or "свидания" in captured.out


@patch("breaker.ui.dialog.storage")
def test_show_templates_list_empty(mock_storage, capsys):
    """Показ списка шаблонов - когда их нет."""
    from breaker.ui.dialog import _show_templates_list
    mock_storage.list_templates.return_value = []
    _show_templates_list()
    captured = capsys.readouterr()
    assert "нет" in captured.out.lower() or "пока" in captured.out.lower()


@patch("breaker.ui.dialog.storage")
def test_show_templates_list_with_data(mock_storage, capsys):
    """Показ списка шаблонов - когда они есть."""
    from breaker.ui.dialog import _show_templates_list
    from breaker.storage.templates import RuleTemplate
    
    mock_storage.list_templates.return_value = [
        RuleTemplate(
            id="test_1",
            name="Тест",
            signal="сигнал",
            action="действие",
            target="цель",
            action_type="open_file",
        )
    ]
    _show_templates_list()
    captured = capsys.readouterr()
    assert "Тест" in captured.out


@patch("breaker.ui.dialog.storage")
def test_create_from_template_no_templates(mock_storage, capsys):
    """Создание из шаблона - шаблонов нет."""
    from breaker.ui.dialog import _create_from_template
    mock_storage.list_templates.return_value = []
    result = _create_from_template()
    assert result is None


def test_ask_signal_empty_then_valid():
    """ask_signal() - пустой ответ, потом валидный."""
    from breaker.ui.dialog import ask_signal
    with patch("rich.prompt.Prompt.ask", side_effect=["", "   ", "файл пуст"]):
        result = ask_signal()
    assert result == "файл пуст"


def test_ask_action_empty_then_valid():
    """ask_action() - пустой ответ, потом валидный."""
    from breaker.ui.dialog import ask_action
    with patch("rich.prompt.Prompt.ask", side_effect=["", "напишу функцию"]):
        result = ask_action()
    assert result == "напишу функцию"


def test_ask_target_empty_then_valid():
    """ask_target() - пустой ответ, потом валидный."""
    from breaker.ui.dialog import ask_target
    with patch("rich.prompt.Prompt.ask", side_effect=["", "main.py"]):
        with patch("pathlib.Path.exists", return_value=False):
            result = ask_target("create")
    assert result == "main.py"


@patch("rich.prompt.Confirm.ask", side_effect=[False, False, False])
@patch("breaker.ui.dialog.ask_ritual")
def test_run_dialog_max_attempts(mock_ritual, mock_confirm, capsys):
    """run_dialog() - превышение 3 попыток."""
    from breaker.ui.dialog import run_dialog
    from breaker.core.schema import Ritual, ActionType
    
    mock_ritual.return_value = Ritual(
        signal="сигнал",
        action="действие",
        target="цель",
        action_type=ActionType.OPEN_FILE,
    )
    result = run_dialog()
    assert result is None
    captured = capsys.readouterr()
    assert "Превышено" in captured.out or "завершаем" in captured.out.lower()

# Тест для main_menu с выбором пункта 1 (создать правило)
@patch("breaker.ui.dialog.run_dialog")
@patch("rich.prompt.IntPrompt.ask", side_effect=[1, 0])  # 1 -> правило, 0 -> выход
def test_main_menu_create_rule(mock_dialog, mock_input, capsys):
    from breaker.ui.dialog import main_menu
    from breaker.core.schema import Ritual, ActionType
    mock_dialog.return_value = Ritual(
        signal="сигнал", action="действие", target="цель",
        action_type=ActionType.OPEN_FILE,
    )
    main_menu()
    captured = capsys.readouterr()
    assert "Правило готово" in captured.out


# Тест для main_menu с выбором пункта 2 (шаблон)
@patch("breaker.ui.dialog._create_from_template")
@patch("rich.prompt.IntPrompt.ask", side_effect=[2, 0])
def test_main_menu_use_template(mock_template, mock_input, capsys):
    from breaker.ui.dialog import main_menu
    mock_template.return_value = None
    main_menu()
    captured = capsys.readouterr()
    assert "Отменено" in captured.out or "свидания" in captured.out


# Тест для main_menu с невалидным пунктом
@patch("rich.prompt.IntPrompt.ask", side_effect=[99, 0])
def test_main_menu_invalid_choice(mock_input, capsys):
    from breaker.ui.dialog import main_menu
    main_menu()
    captured = capsys.readouterr()
    assert "Неизвестный пункт" in captured.out


# Тест для _create_from_template с несуществующим ID
@patch("breaker.ui.dialog.storage")
@patch("rich.prompt.Prompt.ask", return_value="nonexistent_id")
def test_create_from_template_not_found(mock_input, mock_storage, capsys):
    from breaker.ui.dialog import _create_from_template
    from breaker.storage.templates import RuleTemplate
    mock_storage.list_templates.return_value = [
        RuleTemplate(id="t1", name="T1", signal="s", action="a",
                     target="t", action_type="open_file")
    ]
    mock_storage.get_template.return_value = None
    result = _create_from_template()
    assert result is None
    captured = capsys.readouterr()
    assert "не найден" in captured.out.lower()