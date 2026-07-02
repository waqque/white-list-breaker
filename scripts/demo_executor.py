"""Демонстрация работы executor.py."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from breaker.engine.executor import open_file, execute_ritual
from breaker.core.schema import Ritual, ActionType

print(" Демонстрация executor.py")

#  Создаём тестовый файл
test_file = Path("demo_test.py")
test_file.write_text("# Demo file\nprint('Hello from demo!')\n")
print(f"\n Создан тестовый файл: {test_file.absolute()}")

print("\n1  Тестируем open_file() с editor='code'...")
try:
    result = open_file(test_file, editor="code")
    print(f" Файл открыт: {result}")
except Exception as e:
    print(f"  Ошибка: {e}")

print("\n2  Тестируем execute_ritual()...")
ritual = Ritual(
    signal="файл пуст",
    action="открыть файл",
    target=str(test_file),
    action_type=ActionType.OPEN_FILE,
)

result = execute_ritual(ritual)
print(f"   Успех: {result.success}")
print(f"   Evidence: {result.evidence_link}")
if result.error_message:
    print(f"   Ошибка: {result.error_message}")

# Не удаляем файл сразу — даём время VS Code открыть его
print("\n Файл demo_test.py остался в директории.")

print(" Демонстрация завершена")
