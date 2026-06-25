# Диалог с пользователем: 3 вопроса + подтверждение правила
# Использует rich для красивого цветного вывода в терминале
# Импортирует Ritual и ActionType из core.schema (от Участника А)


from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# импорт из core.schema (от Участника А)
from breaker.core.schema import Ritual, ActionType

console = Console()


def ask_signal() -> str:
    # Вопрос 1: Какая ситуация блокирует вас?
    # Returns: str: Непустая строка с описанием ситуации

    console.print("\n[bold cyan]Вопрос 1 из 3[/bold cyan]")
    console.print(
        "[dim]Примеры: 'файл пуст', 'не знаю, с чего начать', "
        "'консоль не запущена'[/dim]"
    )

    signal = Prompt.ask(
        "[yellow]Какая ситуация блокирует вас?[/yellow]"
    )

    while not signal.strip():
        console.print("[red]Сигнал не может быть пустым.[/red]")
        signal = Prompt.ask(
            "[yellow]Какая ситуация блокирует вас?[/yellow]"
        )

    return signal.strip()


def ask_action() -> str:
    # Вопрос 2: Что вы сделаете?
    # Returns: str: Непустая строка с описанием действия

    console.print("\n[bold cyan]Вопрос 2 из 3[/bold cyan]")
    console.print(
        "[dim]Примеры: 'напишу шаблон функции'[/dim]"
    )

    action = Prompt.ask(
        "[yellow]Что вы сделаете, когда это произойдёт?[/yellow]"
    )

    while not action.strip():
        console.print("[red]Действие не может быть пустым.[/red]")
        action = Prompt.ask(
            "[yellow]Что вы сделаете?[/yellow]"
        )

    return action.strip()


def ask_target() -> str:
    # Вопрос 3: Какой ресурс открыть/запустить?
    # Returns: str: Непустая строка с путём к файлу или командой

    console.print("\n[bold cyan]Вопрос 3 из 3[/bold cyan]")
    console.print(
        "[dim]Примеры: 'main.py', 'tests/test_main.py'[/dim]"
    )

    target = Prompt.ask(
        "[yellow]Какой ресурс нужно открыть или команду запустить?[/yellow]"
    )

    while not target.strip():
        console.print("[red]Цель не может быть пустой.[/red]")
        target = Prompt.ask(
            "[yellow]Какой ресурс?[/yellow]"
        )

    return target.strip()


def detect_action_type(target: str) -> ActionType:
    # Автоматически определить тип действия по цели.

    """ 
    Логика:
    - Если target содержит 'test' → CREATE_TEST
    - Если target содержит пробел или команды (npm, python и т.д.) → RUN_SHELL
    - Иначе → OPEN_FILE

    Args:
        target: Путь к файлу или команда

    Returns:
        ActionType: Определённый тип действия
    """
    target_lower = target.lower()

    # Создание теста
    if target_lower.startswith(("tests/", "test_")) or "test" in target_lower:
        return ActionType.CREATE_TEST

    # Shell-команда
    shell_keywords = ["npm", "python", "make", "git", "node", "cargo"]
    if " " in target or any(cmd in target_lower for cmd in shell_keywords):
        return ActionType.RUN_SHELL

    # По умолчанию — открытие файла
    return ActionType.OPEN_FILE


def ask_ritual(task_id: str = "demo-task") -> Ritual:
    # Задать 3 вопроса и вернуть объект Ritual.

    """
    Args:
        task_id: Идентификатор задачи (по умолчанию demo-task)

    Returns:
        Ritual: Сформулированное правило «если–то»
    """

    console.print(Panel(
        "[bold cyan]White-sheet-breaker[/bold cyan]\n\n"
        "Давай сформулируем правило «если–то» для старта задачи.\n"
        "Это поможет преодолеть прокрастинацию и начать работу.",
        title="Начало работы",
        border_style="cyan",
        padding=(1, 2)
    ))

    signal = ask_signal()
    action = ask_action()
    target = ask_target()
    action_type = detect_action_type(target)

    ritual = Ritual(
        signal=signal,
        action=action,
        target=target,
        action_type=action_type,
        task_id=task_id,
    )

    return ritual


def confirm_rule(ritual: Ritual) -> bool:
    #Показать правило и запросить подтверждение.

    """"
    Args:
        ritual: Сформулированное правило

    Returns:
        bool: True если пользователь подтвердил, False если отклонил
    """

    console.print()

    # Используем format_rule() если он есть, иначе собираем вручную
    if hasattr(ritual, "format_rule"):
        rule_text = ritual.format_rule()
    else:
        rule_text = f"ЕСЛИ {ritual.signal} → ТО {ritual.action}"

    console.print(Panel(
        f"[bold green]ЕСЛИ:[/bold green]  {ritual.signal}\n"
        f"[bold blue]ТО:[/bold blue]    {ritual.action}\n"
        f"[bold yellow]ЦЕЛЬ:[/bold yellow]  {ritual.target}\n\n"
        f"[dim]Тип действия: {ritual.action_type.value}[/dim]\n"
        f"[dim]Правило: {rule_text}[/dim]",
        title="Ваше правило",
        border_style="green",
        padding=(1, 2)
    ))

    return Confirm.ask(
        "\n[cyan]Подтверждаете правило и готовы начать?[/cyan]",
        default=True
    )


def run_dialog(task_id: str = "demo-task") -> "Ritual | None":
    # Полный цикл диалога: вопросы -> подтверждение -> возврат правила

    """
    Если пользователь отклоняет правило — цикл повторяется (до 3 попыток).

    Args:
        task_id: Идентификатор задачи

    Returns:
        Ritual | None: Подтверждённое правило или None при отмене
    """
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        console.print(f"\n[dim]Попытка {attempt} из {max_attempts}[/dim]")
        ritual = ask_ritual(task_id)

        if confirm_rule(ritual):
            console.print(
                "\n[bold green]Отлично! Правило подтверждено.[/bold green]"
            )
            return ritual
        else:
            console.print(
                "[yellow]Хорошо, давайте попробуем ещё раз.[/yellow]"
            )

    console.print("[red]Превышено число попыток. Завершаем.[/red]")
    return None


# Точка входа для прямого запуска: python -m breaker.ui.dialog
if __name__ == "__main__":
    result = run_dialog()
    if result:
        console.print(f"\n[bold]Итоговое правило:[/bold] {result}")
        if hasattr(result, "format_rule"):
            console.print(f"[bold]Формат:[/bold] {result.format_rule()}")
        if hasattr(result, "to_dict"):
            console.print(f"[dim]Словарь:[/dim] {result.to_dict()}")