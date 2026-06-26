# CLI-редактор шаблонов правил «если–то».
# Позволяет пользователю просматривать список сохранённых шаблонов.
# Шаблоны хранятся через TemplateStorage (от Участника Б).

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import IntPrompt

from breaker.storage.templates import TemplateStorage

console = Console()

# Глобальный экземпляр хранилища.
# Пользовательские шаблоны сохраняются в ~/.white-sheet-breaker/templates.json
storage = TemplateStorage()


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


def main_menu() -> None:
    # Главное меню редактора.
    while True:
        console.print(Panel(
            "[1] Показать все шаблоны\n"
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
        else:
            console.print("[red]Неизвестный пункт.[/red]")


if __name__ == "__main__":
    main_menu()