# Диалог с пользователем: 3 вопроса + выбор режима + подтверждение правила
# Использует rich для красивого цветного вывода в терминале
# Импортирует Ritual и ActionType из core.schema (от Участника А)
# Интегрирован с TemplateStorage (от Участника Б) для работы с шаблонами


from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt

# импорт из core.schema (от Участника А)
from breaker.core.schema import Ritual, ActionType

# импорт из storage (от Участника Б)
from breaker.storage.templates import TemplateStorage

console = Console()

# Глобальный экземпляр хранилища шаблонов
storage = TemplateStorage()


def ask_signal() -> str:
    # Вопрос 1: Какая ситуация блокирует вас?
    # Returns: str: Непустая строка с описанием ситуации

    console.print("\n[bold cyan]Вопрос 1 из 3[/bold cyan]")
    console.print(
        "[dim]Примеры: 'файл пуст'[/dim]"
    )

    signal = Prompt.ask("[yellow]Какая ситуация блокирует вас?[/yellow]")

    while not signal.strip():
        console.print("[red]Сигнал не может быть пустым.[/red]")
        signal = Prompt.ask("[yellow]Какая ситуация блокирует вас?[/yellow]")

    return signal.strip()


def ask_action() -> str:
    # Вопрос 2: Что вы сделаете?
    # Returns: str: Непустая строка с описанием действия

    console.print("\n[bold cyan]Вопрос 2 из 3[/bold cyan]")
    console.print("[dim]Примеры: 'напишу шаблон функции'[/dim]")

    action = Prompt.ask("[yellow]Что вы сделаете, когда это произойдёт?[/yellow]")

    while not action.strip():
        console.print("[red]Действие не может быть пустым.[/red]")
        action = Prompt.ask("[yellow]Что вы сделаете?[/yellow]")

    return action.strip()


def ask_file_mode() -> str:
    # Вопрос 3: Создать новый файл и открыть его или открыть уже существующий файл?
    # Returns: str: "create" или "open"

    console.print("\n[bold cyan]Вопрос 3 из 3[/bold cyan]")
    console.print(
        "  • [green][1] Создать файл[/green] — создать новый пустой файл и открыть его\n"
        "  • [green][2] Открыть файл[/green] — открыть уже существующий файл"
    )

    while True:
        choice = Prompt.ask(
            "\n[yellow]Ваш выбор (1 или 2)[/yellow]",
            choices=["1", "2"],
            default="1",
        )
        if choice == "1":
            return "create"
        elif choice == "2":
            return "open"


def ask_target(file_mode: str) -> str:
    # Вопрос 4: Какой файл создать или открыть?
    # Returns: str: Непустая строка с путём к файлу

    if file_mode == "create":
        console.print("[dim]Примеры: 'main.py', 'README.md'[/dim]")

        while True:
            target = Prompt.ask("[yellow]Как назвать новый файл?[/yellow]")

            if not target.strip():
                console.print("[red]Имя файла не может быть пустым.[/red]")
                continue

            target = target.strip()
            target_path = Path(target)

            if target_path.exists():
                console.print(
                    f"[red]Файл '{target}' уже существует.[/red]\n"
                    "[dim]Выберите другое имя или используйте режим 'Открыть файл'.[/dim]"
                )
                continue

            return target

    else:  # file_mode == "open"
        console.print("[dim]Примеры: 'main.py', 'README.md'[/dim]")

        while True:
            target = Prompt.ask("[yellow]Какой файл открыть?[/yellow]")

            if not target.strip():
                console.print("[red]Путь к файлу не может быть пустым.[/red]")
                continue

            target = target.strip()
            target_path = Path(target)

            if not target_path.exists():
                console.print(
                    f"[red]Файл '{target}' не найден.[/red]\n"
                    "[dim]Проверьте путь или используйте режим 'Создать файл'.[/dim]"
                )
                continue

            return target


def detect_action_type(target: str, file_mode: str) -> ActionType:
    """Автоматически определить тип действия.

    Логика:
    - Если режим "create" -> CREATE_TEST (используем для создания любых файлов)
    - Если режим "open" и target содержит 'test' -> CREATE_TEST
    - Иначе -> OPEN_FILE

    Args:
        target: Путь к файлу
        file_mode: "create" или "open"

    Returns:
        ActionType: OPEN_FILE или CREATE_TEST
    """
    target_lower = target.lower()

    # Если пользователь выбрал "Создать файл" — используем CREATE_TEST
    # (create_test() в executor.py умеет создавать любые файлы)
    if file_mode == "create":
        return ActionType.CREATE_TEST

    # Если режим "Открыть файл" — проверяем, это тест?
    if target_lower.startswith(("tests/", "test_")) or "test" in target_lower:
        return ActionType.CREATE_TEST

    # По умолчанию — открытие существующего файла
    return ActionType.OPEN_FILE


def ask_ritual(task_id: str = "demo-task") -> Ritual:
    # Задать вопросы и вернуть объект Ritual.

    """
    Args:
        task_id: Идентификатор задачи (по умолчанию demo-task)

    Returns:
        Ritual: Сформулированное правило «если–то»
    """

    console.print(
        Panel(
            "[bold cyan]White-sheet-breaker[/bold cyan]\n\n"
            "Давай сформулируем правило «если–то» для старта задачи.\n"
            "Это поможет преодолеть прокрастинацию и начать работу.",
            title="Начало работы",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    signal = ask_signal()
    action = ask_action()
    file_mode = ask_file_mode()
    target = ask_target(file_mode)
    action_type = detect_action_type(target, file_mode)

    ritual = Ritual(
        signal=signal,
        action=action,
        target=target,
        action_type=action_type,
        task_id=task_id,
    )

    return ritual


def confirm_rule(ritual: Ritual) -> bool:
    # Показать правило и запросить подтверждение.

    """ "
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
        rule_text = f"ЕСЛИ {ritual.signal} -> ТО {ritual.action}"

    console.print(
        Panel(
            f"[bold green]ЕСЛИ:[/bold green]  {ritual.signal}\n"
            f"[bold blue]ТО:[/bold blue]    {ritual.action}\n"
            f"[bold yellow]ЦЕЛЬ:[/bold yellow]  {ritual.target}\n\n"
            f"[dim]Тип действия: {ritual.action_type.value}[/dim]\n"
            f"[dim]Правило: {rule_text}[/dim]",
            title="Ваше правило",
            border_style="green",
            padding=(1, 2),
        )
    )

    return Confirm.ask("\n[cyan]Подтверждаете правило и готовы начать?[/cyan]", default=True)


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
            console.print("\n[bold green]Отлично! Правило подтверждено.[/bold green]")
            return ritual
        else:
            console.print("[yellow]Хорошо, давайте попробуем ещё раз.[/yellow]")

    console.print("[red]Превышено число попыток. Завершаем.[/red]")
    return None


def _show_templates_list() -> None:
    # Показать список шаблонов в виде таблицы.

    templates = storage.list_templates()

    if not templates:
        console.print("[yellow]Шаблонов пока нет. Создайте первый в редакторе.[/yellow]")
        return

    from rich.table import Table

    table = Table(title="Доступные шаблоны")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Название", style="white")
    table.add_column("Сигнал", style="green")
    table.add_column("Действие", style="yellow")
    table.add_column("Цель", style="blue")

    for tpl in templates:
        table.add_row(
            tpl.id,
            tpl.name,
            tpl.signal,
            tpl.action,
            tpl.target,
        )

    console.print(table)


def _create_from_template() -> "Ritual | None":
    # Создать правило на основе выбранного шаблона.

    """
    Показывает список шаблонов, позволяет выбрать один и
    скорректировать поля перед подтверждением.

    Returns:
        Ritual | None: Подтверждённое правило или None при отмене
    """
    templates = storage.list_templates()

    if not templates:
        console.print("[yellow]Шаблонов нет. Сначала создайте их в редакторе.[/yellow]")
        return None

    _show_templates_list()

    template_id = Prompt.ask("\n[cyan]Введите ID шаблона[/cyan]")
    template = storage.get_template(template_id)

    if template is None:
        console.print(f"[red]Шаблон '{template_id}' не найден.[/red]")
        return None

    console.print(
        Panel(
            f"[bold]Шаблон:[/bold] {template.name}\n"
            f"[dim]Сигнал: {template.signal}[/dim]\n"
            f"[dim]Действие: {template.action}[/dim]\n"
            f"[dim]Цель: {template.target}[/dim]",
            title="Выбранный шаблон",
            border_style="magenta",
        )
    )

    console.print(
        "\n[dim]Можете скорректировать значения или нажать Enter для использования по умолчанию[/dim]"
    )

    signal = Prompt.ask("[yellow]Сигнал (если...)[/yellow]", default=template.signal)
    action = Prompt.ask("[yellow]Действие (то...)[/yellow]", default=template.action)
    target = Prompt.ask("[yellow]Цель (ресурс)[/yellow]", default=template.target)
    action_type = detect_action_type(target, "create")

    ritual = Ritual(
        signal=signal,
        action=action,
        target=target,
        action_type=action_type,
        task_id=template.id,
    )

    if confirm_rule(ritual):
        console.print("\n[bold green]Правило создано из шаблона![/bold green]")
        return ritual
    else:
        console.print("[yellow]Отменено.[/yellow]")
        return None


def main_menu() -> None:
    """
    Позволяет пользователю:
    - Создать правило с нуля
    - Использовать готовый шаблон
    - Открыть редактор шаблонов    - Выйти из программы
    """
    console.print(
        Panel(
            "[bold magenta]White-sheet-breaker[/bold magenta]\n\n"
            "[dim]Инструмент для преодоления прокрастинации через правила «если–то»[/dim]",
            border_style="magenta",
            title="Главное меню",
        )
    )

    while True:
        console.print(
            Panel(
                "[1] Создать правило с нуля\n"
                "[2] Использовать готовый шаблон\n"
                "[3] Управление шаблонами (редактор)\n"
                "[0] Выход",
                title="Что хотите сделать?",
                border_style="cyan",
            )
        )

        try:
            choice = IntPrompt.ask("Выберите пункт", default=0)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Выход...[/dim]")
            break

        if choice == 0:
            console.print("[dim]До свидания![/dim]")
            break
        elif choice == 1:
            try:
                ritual = run_dialog()
                if ritual:
                    console.print(
                        f"\n[bold green]Правило готово:[/bold green] "
                        f"{ritual.format_rule() if hasattr(ritual, 'format_rule') else ritual}"
                    )
            except KeyboardInterrupt:
                console.print("\n[yellow]Диалог прерван.[/yellow]")
        elif choice == 2:
            try:
                ritual = _create_from_template()
                if ritual:
                    console.print(
                        f"\n[bold green]Правило готово:[/bold green] "
                        f"{ritual.format_rule() if hasattr(ritual, 'format_rule') else ritual}"
                    )
            except KeyboardInterrupt:
                console.print("\n[yellow]Выбор шаблона прерван.[/yellow]")
        elif choice == 3:
            try:
                from breaker.ui.template_editor import main_menu as editor_menu

                editor_menu()
            except KeyboardInterrupt:
                console.print("\n[yellow]Редактор закрыт.[/yellow]")
        else:
            console.print("[red]Неизвестный пункт. Выберите 0-3.[/red]")


# Точка входа для прямого запуска: python -m breaker.ui.dialog
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[dim]Программа завершена.[/dim]")