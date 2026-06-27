# 11 passed
from unittest.mock import patch
from breaker.core.schema import Ritual, ActionType
from breaker.ui.dialog import (
    ask_signal,
    ask_action,
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


@patch("rich.prompt.Prompt.ask", return_value="main.py")
def test_ask_target(mock_input):
    # Проверяем, что ask_target возвращает введённую строку.
    result = ask_target()
    assert result == "main.py"


def test_detect_action_type_open_file():
    # Тест определения типа действия: открытие файла.
    assert detect_action_type("main.py") == ActionType.OPEN_FILE
    assert detect_action_type("src/app.js") == ActionType.OPEN_FILE
    assert detect_action_type("example.py") == ActionType.OPEN_FILE


def test_detect_action_type_run_shell():
    # Тест определения типа действия: запуск команды.
    assert detect_action_type("npm start") == ActionType.RUN_SHELL
    assert detect_action_type("python main.py") == ActionType.RUN_SHELL
    assert detect_action_type("git status") == ActionType.RUN_SHELL
    assert detect_action_type("make lint") == ActionType.RUN_SHELL


def test_detect_action_type_create_test():
    # Тест определения типа действия: создание теста.
    assert detect_action_type("tests/test_main.py") == ActionType.CREATE_TEST
    assert detect_action_type("test_app.js") == ActionType.CREATE_TEST
    assert detect_action_type("my_test.py") == ActionType.CREATE_TEST


@patch("rich.prompt.Prompt.ask", side_effect=["файл пуст", "напишу функцию", "main.py"])
def test_ask_ritual(mock_input):
    # Проверяем, что ask_ritual возвращает объект Ritual.
    ritual = ask_ritual(task_id="test-task")
    assert isinstance(ritual, Ritual)
    assert ritual.signal == "файл пуст"
    assert ritual.action == "напишу функцию"
    assert ritual.target == "main.py"
    assert ritual.action_type == ActionType.OPEN_FILE
    assert ritual.task_id == "test-task"


@patch("rich.prompt.Prompt.ask", side_effect=["консоль не запущена", "запущу npm", "npm start"])
def test_ask_ritual_shell_command(mock_input):
    # Проверяем, что ask_ritual определяет shell-команду.
    ritual = ask_ritual()
    assert ritual.action_type == ActionType.RUN_SHELL


@patch("rich.prompt.Prompt.ask", side_effect=["нужен тест", "создам тест", "tests/test_main.py"])
def test_ask_ritual_create_test(mock_input):
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
