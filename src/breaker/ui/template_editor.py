# CLI-редактор шаблонов правил «если–то».
# Позволяет пользователю:
# - Просматривать список сохранённых шаблонов
# - Создавать новые шаблоны
# Шаблоны хранятся через TemplateStorage (от Участника Б).

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

from breaker.core.schema import ActionType
from breaker.storage.templates import TemplateStorage, RuleTemplate

console = Console()

# Глобальный экземпляр хранилища.
# Пользовательские шаблоны сохраняются в ~/.white-sheet-breaker/templates.json
storage = TemplateStorage()


def _action_type_from_str(choice: str) -> str:
    # Преобразовать выбор пользователя в строку action_type.
    # RuleTemplate хранит action_type как str
    action_type_map = {
        "1": ActionType.OPEN_FILE.value,
        "2": ActionType.RUN_SHELL.value,
        "3": ActionType.CREATE_TEST.value,
    }
    return action_type_map[choice]


def list_templates_ui() -> None:
    # Показать список всех шаблонов в виде таблицы.
    console.print(Panel(
        "[bold]Список сохранённых шаблонов[/bold]",
        border_style="cyan"
    ))

    templates = storage.list_templates()

    if not templates:
        console.print("[yellow]Шаблонов пока нет. Создайте первый.[/yellow]")
        return

    table = Table(title="Шаблоны правил «если–то»")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Название", style="white")
    table.add_column("Сигнал (если...)", style="green")
    table.add_column("Действие (то...)", style="yellow")
    table.add_column("Цель", style="blue")
    table.add_column("Тип", style="magenta")
    table.add_column("Тип шаблона", style="red")

    for tpl in templates:
        if tpl.is_system:
            tpl_type = "[bold red]системный[/bold red]"
        else:
            tpl_type = "[dim]пользовательский[/dim]"

        table.add_row(
            tpl.id,
            tpl.name,
            tpl.signal,
            tpl.action,
            tpl.target,
            tpl.action_type,
            tpl_type,
        )

    console.print(table)
    console.print(f"\n[dim]Всего: {len(templates)} шаблонов[/dim]")


def create_template_ui() -> None:
    # Создать новый шаблон.
    console.print(Panel(
        "[bold]Создание нового шаблона[/bold]",
        border_style="green"
    ))

    name = Prompt.ask("Название шаблона")
    signal = Prompt.ask("Сигнал (если...)")
    action = Prompt.ask("Действие (то...)")
    target = Prompt.ask("Цель (ресурс)")
    description = Prompt.ask("Описание (необязательно)", default="")

    console.print("\n[bold]Тип действия:[/bold]")
    console.print("  1. [green]open_file[/green]   — открыть файл")
    console.print("  2. [green]run_shell[/green]   — выполнить команду")
    console.print("  3. [green]create_test[/green] — создать тест")
    choice = Prompt.ask("Номер", choices=["1", "2", "3"], default="1")

    # Генерируем уникальный ID для пользовательского шаблона
    user_templates = [t for t in storage.list_templates() if not t.is_system]
    template_id = f"user-{len(user_templates) + 1:03d}"

    new_template = RuleTemplate(
        id=template_id,
        name=name,
        signal=signal,
        action=action,
        target=target,
        action_type=_action_type_from_str(choice),
        description=description,
        is_system=False,
    )

    # Сохраняем через storage (в ~/.white-sheet-breaker/templates.json)
    success = storage.save_template(new_template)

    if success:
        console.print(f"\n[green]Шаблон {template_id} создан.[/green]")
    else:
        console.print(f"\n[red]Ошибка создания шаблона.[/red]")


def main_menu() -> None:
    # Главное меню редактора.
    while True:
        console.print(Panel(
            "[1] Показать все шаблоны\n"
            "[2] Создать шаблон\n"
            "[0] Выход",
            title="Редактор шаблонов",
            border_style="magenta"
        ))

        choice = IntPrompt.ask("Выберите пункт", default=0)

        if choice == 0:
            console.print("[dim]До свидания.[/dim]")
            break
        elif choice == 1:
            list_templates_ui()
        elif choice == 2:
            create_template_ui()
        else:
            console.print("[red]Неизвестный пункт.[/red]")


if __name__ == "__main__":
    main_menu()