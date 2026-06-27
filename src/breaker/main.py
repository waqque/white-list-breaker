"""Оркестратор модуля White-sheet-breaker.
Связывает UI, Engine и Core в единый цикл работы.
"""
import argparse
import sys

# Импорт модулей участников
from breaker.ui.dialog import run_dialog, ask_ritual
from breaker.ui.timer import run_timer_with_prompt
from breaker.engine.executor import execute_ritual

# Импорт твоих модулей (Core)
from breaker.core.schema import Ritual, RitualResult, ActionType
from breaker.core.tracker import log_ritual_result
from breaker.core.xapi_client import send_statement, LrsConfig


def run_demo():
    """Демонстрация работы ядра без UI (с тестовым правилом)."""
    print("🎬 Запуск демонстрации White-sheet-breaker...\n")
    
    # Создаём тестовый ритуал с create_test (не требует существующего файла)
    ritual = Ritual(
        signal="нужно написать тест",
        action="создам шаблон теста",
        target="demo_test.py",  # Новый файл, который будет создан
        action_type=ActionType.CREATE_TEST,
        task_id="demo-task",
    )
    print(f"📝 Тестовое правило: {ritual.format_rule()}")
    
    # Выполняем действие
    print("\n⚙️  Выполняю действие...")
    result = execute_ritual(ritual)
    
    # Логируем
    log_file = log_ritual_result(result)
    print(f"📊 Результат записан в лог: {log_file}")
    
    # Отправляем xAPI
    print("📡 Отправка события в LRS...")
    config = LrsConfig.from_env()
    send_statement(result, config)
    
    print("\n✅ Демонстрация завершена.")

def run_full_cycle():
    """Полный цикл: Диалог -> Исполнение -> Таймер -> Лог -> xAPI."""
    print(" Запуск White-sheet-breaker...\n")

    # 1. UI: Получаем правило от пользователя (с подтверждением)
    try:
        ritual = run_dialog()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
        return
    except Exception as e:
        print(f"Ошибка в диалоге: {e}")
        return

    if ritual is None:
        print(" Пользователь отменил действие.")
        return

    print(f"Правило принято: {ritual.format_rule()}\n")

    # 2. Engine: Выполняем микро-шаг
    print("Выполняю действие...")
    try:
        result = execute_ritual(ritual)
    except Exception as e:
        print(f" Ошибка при выполнении: {e}")
        return

    # 3. UI: Запускаем Pomodoro-таймер (если действие успешно)
    if result.success:
        print("\nТеперь сосредоточься на задаче!")
        try:
            timer_completed = run_timer_with_prompt()
            if timer_completed:
                print("Pomodoro завершён!")
            else:
                print("Pomodoro прерван.")
        except Exception as e:
            print(f"Ошибка таймера: {e}")

    # 4. Core: Логируем результат
    log_file = log_ritual_result(result)
    print(f"Результат записан в лог: {log_file}")

    # 5. Core: Отправляем xAPI-стейтмент
    print("Отправка события в LRS...")
    config = LrsConfig.from_env()
    success = send_statement(result, config)
    
    if success:
        print("\nРитуал успешно завершён!")
    else:
        print("\nРитуал выполнен, но не удалось отправить событие в LRS.")


def main():
    parser = argparse.ArgumentParser(description="White-sheet-breaker CLI")
    parser.add_argument(
        "--demo", 
        action="store_true", 
        help="Запустить демо-сценарий без UI (с тестовым правилом)"
    )
    parser.add_argument(
        "--no-timer",
        action="store_true",
        help="Запустить без Pomodoro-таймера"
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        run_full_cycle()


if __name__ == "__main__":
    main()