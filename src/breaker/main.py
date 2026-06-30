"""Оркестратор модуля White-sheet-breaker.
Связывает UI, Engine, Storage и Core в единый цикл работы.

Участники:
- А (Core): schema.py, tracker.py, xapi_client.py
- Б (Engine/Storage): executor.py, templates.py, file_templates.py
- В (UI): dialog.py, timer.py, template_editor.py, activity_monitor.py, help_menu.py
"""

import argparse
import sys
from pathlib import Path
import threading
import signal

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt, Confirm
from rich.table import Table

# Импорт модулей Участника В (UI)
from breaker.ui.dialog import run_dialog
from breaker.ui.timer import run_timer_with_prompt
from breaker.ui.template_editor import main_menu as editor_menu
from breaker.ui.activity_monitor import ActivityMonitor
from breaker.ui.help_menu import (
    show_help_level1,
    show_help_level2,
    apply_help_choice,
    show_success_message,
)

# Импорт модулей Участника Б (Engine + Storage)
from breaker.engine.executor import execute_ritual
from breaker.storage.templates import TemplateStorage

# Импорт модулей Участника А (Core)
from breaker.core.schema import Ritual, RitualResult, ActionType
from breaker.core.tracker import log_ritual_result
from breaker.core.xapi_client import send_statement, LrsConfig

console = Console()

# Глобальные переменные для управления прогрессом и мониторингом
_progress_paused = False
_current_monitor = None
_monitor_thread = None


def set_progress_paused(paused: bool):
    """Приостановить/возобновить обновление прогресса."""
    global _progress_paused
    _progress_paused = paused


def signal_handler(signum, frame):
    """Обработчик сигнала Ctrl+C."""
    global _current_monitor, _monitor_thread
    
    console.print("\n[yellow]⏸️ Получен сигнал прерывания...[/yellow]")
    
    # Если есть активный монитор - останавливаем его
    if _current_monitor:
        _current_monitor.set_interrupted()
    
    # Если есть поток мониторинга - ждём его завершения
    if _monitor_thread and _monitor_thread.is_alive():
        console.print("[dim]Ожидаем завершения мониторинга...[/dim]")
        _monitor_thread.join(timeout=2)
    
    # Выходим из программы
    console.print("\n[dim]👋 До свидания! Удачи в работе![/dim]\n")
    sys.exit(0)


# ============================================================================
# Главное меню
# ============================================================================
def show_welcome():
    """Показать приветственный экран."""
    console.print()
    console.print(
        Panel.fit(
            "[bold magenta]White-sheet-breaker[/bold magenta]\n"
            "[dim]Инструмент для преодоления прокрастинации через правила «если-то»[/dim]\n\n"
            "[cyan]Гипотеза:[/cyan] Превращение размытого намерения в конкретное\n"
            "правило «ЕСЛИ [сигнал] → ТО [действие]» и немедленное выполнение\n"
            "микро-шага снижает психологическое сопротивление.",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def show_main_menu():
    """Показать главное меню и вернуть выбор пользователя."""
    console.print()
    console.print(
        Panel(
            "[bold white][1][/bold white] 🎯 Создать правило с нуля\n"
            "[bold white][2][/bold white] 📋 Использовать готовый шаблон\n"
            "[bold white][3][/bold white] 📚 Управление шаблонами (редактор)\n"
            "[bold white][4][/bold white] 🎬 Демо-режим (полный цикл без ввода)\n"
            "[bold white][5][/bold white] 📊 Посмотреть статистику (логи)\n"
            "[bold white][0][/bold white] 🚪 Выход",
            title="[bold cyan]Что хотите сделать?[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    try:
        choice = IntPrompt.ask("Выберите пункт", default=0)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Выход...[/dim]")
        return 0
    return choice


# ============================================================================
# Фоновое наблюдение с помощью ActivityMonitor
# ============================================================================
def run_with_monitoring(ritual: Ritual, blocking: bool = False) -> threading.Thread | None:
    """Запустить фоновое наблюдение за активностью пользователя."""
    global _current_monitor, _monitor_thread
    
    # Определяем файлы для наблюдения
    watched_files = []
    if ritual.action_type in [ActionType.OPEN_FILE, ActionType.CREATE_TEST]:
        watched_files.append(Path(ritual.target))

    if not watched_files:
        console.print("[yellow]⚠️ Нет файлов для наблюдения[/yellow]")
        return None

    # Создаём монитор
    monitor = ActivityMonitor(
        watched_files=watched_files,
        idle_threshold_level1=30,   # 30 секунд
        idle_threshold_level2=60,   # 1 минута
        idle_threshold_timeout=90,  # 1.5 минуты
        activity_threshold=25,
        check_interval=5,
        help_level1_callback=lambda: show_help_level1(watched_files[0]),
        help_level2_callback=lambda: show_help_level2(watched_files[0]),
        apply_choice_callback=lambda choice, level: apply_help_choice(choice, watched_files[0], level),
        success_callback=lambda info: show_success_message(watched_files[0], info),
        progress_refresh_callback=set_progress_paused,
    )
    
    _current_monitor = monitor

    def _run_monitor():
        try:
            result = monitor.start_monitoring()
            if result == "success":
                console.print("[green]🎉 Отлично! Вы начали работу.[/green]")
            elif result == "timeout":
                console.print("[yellow]⏰ Сессия завершена из-за неактивности.[/yellow]")
            elif result == "interrupted":
                console.print("[yellow]⏸️ Мониторинг прерван пользователем.[/yellow]")
            else:
                console.print("[dim]👋 Мониторинг завершён.[/dim]")
        except Exception as e:
            console.print(f"[red]❌ Ошибка мониторинга: {e}[/red]")
        finally:
            _current_monitor = None

    if blocking:
        _run_monitor()
        return None
    else:
        thread = threading.Thread(target=_run_monitor, daemon=True)
        thread.start()
        _monitor_thread = thread
        return thread


# ============================================================================
# Полный цикл: правило → выполнение → (опционально таймер) → наблюдение → лог → xAPI
# ============================================================================
def run_full_cycle(ritual: Ritual, skip_timer: bool = False) -> RitualResult:
    """Выполнить полный цикл работы модуля."""
    global _monitor_thread
    
    console.print()
    console.print(
        Panel(
            f"[bold green]Правило:[/bold green] {ritual.format_rule()}\n"
            f"[dim]Тип действия:[/dim] {ritual.action_type.value}\n"
            f"[dim]Цель:[/dim] {ritual.target}",
            title="[bold cyan]Шаг 1/4: Правило сформулировано[/bold cyan]",
            border_style="green",
        )
    )

    # Шаг 2: Выполнение действия (Участник Б)
    console.print()
    console.print("[bold cyan]Шаг 2/4: Выполняю микро-шаг...[/bold cyan]")
    result = execute_ritual(ritual)

    if result.success:
        console.print(f"[green]✅ Действие выполнено успешно[/green]")
        console.print(f"[dim]   Evidence: {result.evidence_link}[/dim]")
    else:
        console.print(f"[red]❌ Ошибка: {result.error_message}[/red]")

    # Шаг 3: Опциональный Pomodoro-таймер + фоновое наблюдение
    monitor_thread = None
    monitor_started = False

    if result.success and not skip_timer:
        console.print()
        console.print("[bold cyan]Шаг 3/4: Что дальше?[/bold cyan]")

        # Спрашиваем про таймер
        try:
            start_timer = Confirm.ask(
                "\n[cyan]Запустить Pomodoro-таймер для концентрации?[/cyan]",
                default=True,
            )
        except (KeyboardInterrupt, EOFError):
            start_timer = False

        # Запускаем фоновое наблюдение (если это файл)
        if ritual.action_type in [ActionType.OPEN_FILE, ActionType.CREATE_TEST]:
            console.print()
            console.print("[bold cyan]👀 Запускаю фоновое наблюдение...[/bold cyan]")
            console.print("[dim]Модуль поможет, если вы зависнете.[/dim]")
            monitor_thread = run_with_monitoring(ritual, blocking=False)
            monitor_started = True

        # Запускаем таймер (параллельно с наблюдением)
        if start_timer:
            console.print()
            console.print("[dim]Сосредоточься на задаче![/dim]")
            try:
                timer_completed = run_timer_with_prompt()
                if timer_completed:
                    console.print("[green]🎉 Pomodoro завершён![/green]")
                else:
                    console.print("[yellow]⏸️ Pomodoro прерван.[/yellow]")
            except KeyboardInterrupt:
                console.print("\n[yellow]⏸️ Таймер прерван пользователем.[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка таймера: {e}[/yellow]")

        # Если мониторинг запущен, ждём его завершения
        if monitor_started and monitor_thread:
            console.print()
            console.print("[dim]⏳ Ожидаем вашу активность в файле...[/dim]")
            console.print("[dim](Начните редактировать файл, чтобы завершить наблюдение)[/dim]")
            console.print("[dim](Нажмите Ctrl+C для прерывания)[/dim]")
            
            try:
                monitor_thread.join()
            except KeyboardInterrupt:
                console.print("\n[yellow]⏸️ Ожидание прервано пользователем.[/yellow]")

            if monitor_thread.is_alive():
                console.print("[yellow]⚠️ Мониторинг всё ещё работает, но мы продолжаем...[/yellow]")
            else:
                console.print("[dim]✅ Наблюдение завершено[/dim]")
            
            _monitor_thread = None

    # Шаг 4: Логирование + xAPI (Участник А)
    console.print()
    console.print("[bold cyan]Шаг 4/4: Фиксирую результат...[/bold cyan]")

    # Логируем в NDJSON
    log_file = log_ritual_result(result)
    console.print(f"[dim]📝 Записано в лог: {log_file}[/dim]")

    # Отправляем xAPI-стейтмент
    config = LrsConfig.from_env()
    xapi_success = send_statement(result, config)

    if xapi_success:
        console.print("[green]📡 xAPI-стейтмент отправлен[/green]")
    else:
        console.print("[yellow]⚠️ Не удалось отправить xAPI-стейтмент[/yellow]")

    # Финальное сообщение
    console.print()
    if result.success:
        console.print(
            Panel.fit(
                "[bold green]🎉 Ритуал успешно завершён![/bold green]\n"
                "[dim]Ты сделал первый шаг. Продолжай в том же духе![/dim]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold yellow]⚠️ Ритуал завершён с ошибкой[/bold yellow]\n"
                "[dim]Это нормально. Попробуй ещё раз с другим правилом.[/dim]",
                border_style="yellow",
            )
        )

    return result


# ============================================================================
# Режим 1: Создание правила с нуля
# ============================================================================
def mode_create_from_scratch(skip_timer: bool = False):
    """Создать правило через диалог и выполнить его."""
    console.print()
    console.print("[bold cyan]🎯 Создаём новое правило «если-то»[/bold cyan]")

    try:
        ritual = run_dialog()
    except KeyboardInterrupt:
        console.print("\n[yellow]Диалог прерван.[/yellow]")
        return
    except Exception as e:
        console.print(f"[red]❌ Ошибка в диалоге: {e}[/red]")
        return

    if ritual is None:
        console.print("[yellow]Пользователь отменил действие.[/yellow]")
        return

    run_full_cycle(ritual, skip_timer=skip_timer)


# ============================================================================
# Режим 2: Использование шаблона
# ============================================================================
def mode_use_template(skip_timer: bool = False):
    """Выбрать шаблон, адаптировать и выполнить."""
    console.print()
    console.print("[bold cyan]📋 Используем готовый шаблон[/bold cyan]")

    storage = TemplateStorage()
    templates = storage.list_templates()

    if not templates:
        console.print("[yellow]Шаблонов пока нет. Создайте первый в редакторе.[/yellow]")
        return

    # Показываем таблицу шаблонов
    table = Table(title="Доступные шаблоны")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Название", style="white")
    table.add_column("Сигнал", style="green")
    table.add_column("Действие", style="yellow")
    table.add_column("Цель", style="blue")
    table.add_column("Тип", style="magenta")

    for tpl in templates:
        table.add_row(
            tpl.id,
            tpl.name,
            tpl.signal,
            tpl.action,
            tpl.target,
            tpl.action_type,
        )
    console.print(table)

    # Выбор шаблона
    template_id = Prompt.ask("\n[cyan]Введите ID шаблона[/cyan]")
    template = storage.get_template(template_id)

    if template is None:
        console.print(f"[red]❌ Шаблон '{template_id}' не найден.[/red]")
        return

    # Показываем шаблон и даём возможность адаптировать
    console.print()
    console.print(
        Panel(
            f"[bold]Шаблон:[/bold] {template.name}\n"
            f"[green]Сигнал:[/green] {template.signal}\n"
            f"[yellow]Действие:[/yellow] {template.action}\n"
            f"[blue]Цель:[/blue] {template.target}\n"
            f"[magenta]Тип:[/magenta] {template.action_type}\n"
            f"[dim]{template.description}[/dim]",
            title="[bold cyan]Выбранный шаблон[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print(
        "\n[dim]Можете скорректировать значения или нажать Enter для использования по умолчанию[/dim]"
    )

    signal = Prompt.ask("[yellow]Сигнал (если...)[/yellow]", default=template.signal)
    action = Prompt.ask("[yellow]Действие (то...)[/yellow]", default=template.action)
    target = Prompt.ask("[yellow]Цель (ресурс)[/yellow]", default=template.target)

    # Конвертируем шаблон в Ritual
    try:
        ritual = template.to_ritual()
        ritual.signal = signal
        ritual.action = action
        ritual.target = target
    except (ValueError, AttributeError) as e:
        console.print(f"[yellow]⚠️ {e}. Создаём правило вручную.[/yellow]")
        try:
            action_type = ActionType(template.action_type)
        except ValueError:
            console.print(f"[red]❌ Неизвестный тип действия: {template.action_type}[/red]")
            return
        ritual = Ritual(
            signal=signal,
            action=action,
            target=target,
            action_type=action_type,
            task_id=template.id,
        )

    # Подтверждение
    from breaker.ui.dialog import confirm_rule

    if not confirm_rule(ritual):
        console.print("[yellow]Отменено.[/yellow]")
        return

    run_full_cycle(ritual, skip_timer=skip_timer)


# ============================================================================
# Режим 4: Демо-режим
# ============================================================================
def run_demo():
    """Демонстрация полного цикла без ввода пользователя."""
    console.print()
    console.print(
        Panel.fit(
            "[bold magenta]🎬 ДЕМО-РЕЖИМ[/bold magenta]\n"
            "[dim]Демонстрация полного цикла работы модуля[/dim]",
            border_style="magenta",
        )
    )

    # Создаём тестовое правило (CREATE_TEST — не требует существующего файла)
    ritual = Ritual(
        signal="нужно написать тест",
        action="создам шаблон теста",
        target="demo_test.py",
        action_type=ActionType.CREATE_TEST,
        task_id="demo-task",
    )

    console.print()
    console.print(
        Panel(
            f"[bold]Тестовое правило:[/bold] {ritual.format_rule()}\n"
            f"[dim]Тип:[/dim] {ritual.action_type.value}\n"
            f"[dim]Цель:[/dim] {ritual.target}\n\n"
            "[cyan]Это правило будет выполнено автоматически.[/cyan]\n"
            "[dim]Создастся файл demo_test.py с шаблоном pytest.[/dim]",
            title="[bold cyan]Демо-сценарий[/bold cyan]",
            border_style="cyan",
        )
    )

    # Выполняем полный цикл (без таймера и наблюдения для быстрого демо)
    run_full_cycle(ritual, skip_timer=True)

    # Показываем созданный файл
    demo_file = Path("demo_test.py")
    if demo_file.exists():
        console.print()
        console.print(
            Panel(
                f"[bold]Содержимое {demo_file}:[/bold]\n\n"
                f"[dim]{demo_file.read_text(encoding='utf-8')}[/dim]",
                title="[bold green]Созданный файл[/bold green]",
                border_style="green",
            )
        )


# ============================================================================
# Режим 5: Статистика
# ============================================================================
def show_stats():
    """Показать статистику по логам."""
    from breaker.core.tracker import get_stats, read_log

    console.print()
    console.print("[bold cyan]📊 Статистика работы модуля[/bold cyan]")

    stats = get_stats()

    if stats["total"] == 0:
        console.print("[yellow]Логов пока нет. Запустите модуль хотя бы раз.[/yellow]")
        return

    # Таблица со статистикой
    table = Table(title="Общая статистика")
    table.add_column("Метрика", style="cyan")
    table.add_column("Значение", style="white", justify="right")

    table.add_row("Всего ритуалов", str(stats["total"]))
    table.add_row("Успешных", f"[green]{stats['success_count']}[/green]")
    table.add_row("С ошибками", f"[red]{stats['fail_count']}[/red]")
    table.add_row(
        "Доля успеха",
        f"[bold]{stats['success_rate']:.0%}[/bold]",
    )

    console.print(table)

    # Таблица по типам действий
    if stats["action_types"]:
        type_table = Table(title="По типам действий")
        type_table.add_column("Тип действия", style="cyan")
        type_table.add_column("Количество", style="white", justify="right")

        for action_type, count in stats["action_types"].items():
            type_table.add_row(action_type, str(count))

        console.print(type_table)

    # Последние 5 записей
    entries = read_log()
    if entries:
        console.print()
        console.print("[bold cyan]Последние 5 ритуалов:[/bold cyan]")
        for entry in entries[-5:]:
            status = "[green]✅[/green]" if entry.get("success") else "[red]❌[/red]"
            console.print(
                f"  {status} [dim]{entry.get('timestamp', '')[:16]}[/dim] "
                f"ЕСЛИ {entry.get('signal', '')} → ТО {entry.get('action', '')}"
            )


# ============================================================================
# Главная функция
# ============================================================================
def main():
    """Главная точка входа модуля."""
    # Устанавливаем обработчик сигнала для Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="White-sheet-breaker — инструмент против прокрастинации",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m breaker                  # Интерактивный режим
  python -m breaker --demo           # Демо-режим
  python -m breaker --no-timer       # Без Pomodoro-таймера и наблюдения
  python -m breaker --demo --no-timer  # Быстрое демо
        """,
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустить демо-сценарий без интерактивного ввода",
    )
    parser.add_argument(
        "--no-timer",
        action="store_true",
        help="Не запускать Pomodoro-таймер и наблюдение после выполнения ритуала",
    )
    args = parser.parse_args()

    # Приветствие
    show_welcome()

    # Демо-режим (по флагу)
    if args.demo:
        run_demo()
        return

    # Интерактивный цикл
    try:
        while True:
            choice = show_main_menu()

            if choice == 0:
                console.print("\n[dim]👋 До свидания! Удачи в работе![/dim]\n")
                break
            elif choice == 1:
                mode_create_from_scratch(skip_timer=args.no_timer)
            elif choice == 2:
                mode_use_template(skip_timer=args.no_timer)
            elif choice == 3:
                try:
                    editor_menu()
                except KeyboardInterrupt:
                    console.print("\n[yellow]Редактор закрыт.[/yellow]")
            elif choice == 4:
                run_demo()
            elif choice == 5:
                show_stats()
            else:
                console.print("[red]❌ Неизвестный пункт. Выберите 0-5.[/red]")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]🚫 Прервано пользователем.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()