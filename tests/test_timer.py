# 5 passed
from unittest.mock import patch
from breaker.ui.timer import ask_duration, pomodoro_timer


@patch('rich.prompt.IntPrompt.ask', return_value=5)
def test_ask_duration_valid(mock_input):
    # Проверяем, что ask_duration возвращает корректное значение.
    result = ask_duration()
    assert result == 5


@patch('rich.prompt.IntPrompt.ask', return_value=1)
def test_ask_duration_minimum(mock_input):
    # Минимальное значение — 1 минута.
    result = ask_duration()
    assert result == 1


@patch('rich.prompt.IntPrompt.ask', return_value=50)
def test_ask_duration_maximum(mock_input):
    # Максимальное значение — 50 минут.
    result = ask_duration()
    assert result == 50


@patch('breaker.ui.timer.time.sleep')
def test_pomodoro_timer_completes(mock_sleep):
    # Таймер должен завершиться без ошибок (0 минут = мгновенное завершение).
    result = pomodoro_timer(minutes=0)
    assert result is True


@patch('rich.prompt.IntPrompt.ask', return_value=10)
@patch('breaker.ui.timer.time.sleep')
def test_run_timer_with_prompt(mock_sleep, mock_input):
    # Полный цикл: спросить минуты -> запустить таймер.
    from breaker.ui.timer import run_timer_with_prompt
    result = run_timer_with_prompt()
    assert result is True