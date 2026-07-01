"""Меню помощи при бездействии пользователя.

Показывает пользователю варианты действий, когда он неактивен.
Адаптируется под тип файла (.py, .md, .json, .yaml, .txt).

Использует FileTemplates из engine/file_templates.py для вставки
шаблонов содержимого в файл.

Интеграция:
- activity_monitor.py: вызывает show_help_level1/level2 через колбэки
- file_templates.py: генерирует шаблоны для вставки
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt

from breaker.engine.file_templates import FileTemplates

console = Console()


def _get_file_type(file_path: Path) -> str:
    """Определить тип файла по расширению."""
    suffix = file_path.suffix.lower()
    type_map = {
        '.py': 'python',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.txt': 'text',
    }
    return type_map.get(suffix, 'other')


def _is_test_file(file_path: Path) -> bool:
    """Проверить, является ли файл тестом."""
    return file_path.name.startswith('test_') or file_path.name.endswith('_test.py')


def show_help_level1(file_path: Path) -> int:
    """Показать меню помощи уровня 1.

    Args:
        file_path: Путь к файлу, за которым наблюдаем.

    Returns:
        int: Выбор пользователя (1..max_choice).
    """
    file_type = _get_file_type(file_path)
    is_test = _is_test_file(file_path)

    console.print()
    console.print(
        Panel(
            "[bold yellow]Похоже, вы пока не начали[/bold yellow]\n\n"
            f"Файл [cyan]{file_path.name}[/cyan] не изменился.\n"
            "Нужна помощь?",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    console.print()

    # Показываем опции в зависимости от типа файла
    if file_type == 'python':
        if is_test:
            console.print("[bold white][1][/bold white] Вставить шаблон теста")
            console.print("[bold white][2][/bold white] Написать TODO")
            console.print("[bold white][3][/bold white] Таймер на 5 минут")
            console.print("[bold white][4][/bold white] Ничего, продолжу сам")
        else:
            console.print("[bold white][1][/bold white] Шаблон функции")
            console.print("[bold white][2][/bold white] Шаблон класса")
            console.print("[bold white][3][/bold white] Написать TODO")
            console.print("[bold white][4][/bold white] Таймер")
            console.print("[bold white][5][/bold white] Ничего, продолжу сам")
    elif file_type == 'markdown':
        console.print("[bold white][1][/bold white] Шаблон Markdown-документа")
        console.print("[bold white][2][/bold white] Написать заголовок")
        console.print("[bold white][3][/bold white] Таймер")
        console.print("[bold white][4][/bold white] Ничего, продолжу сам")
    elif file_type in ('json', 'yaml'):
        console.print(f"[bold white][1][/bold white] Шаблон {file_type.upper()}-файла")
        console.print("[bold white][2][/bold white] Таймер")
        console.print("[bold white][3][/bold white] Ничего, продолжу сам")
    else:
        console.print("[bold white][1][/bold white] Таймер")
        console.print("[bold white][2][/bold white] Ничего, продолжу сам")

    console.print()
    max_choice = _get_max_choice_level1(file_type, is_test)
    choice = IntPrompt.ask("Выберите действие", default=max_choice)

    while choice < 1 or choice > max_choice:
        console.print(f"[red]Выберите число от 1 до {max_choice}[/red]")
        choice = IntPrompt.ask("Выберите действие", default=max_choice)

    return choice


def _get_max_choice_level1(file_type: str, is_test: bool) -> int:
    """Получить максимальный номер выбора для уровня 1."""
    if file_type == 'python':
        return 4 if is_test else 5
    elif file_type == 'markdown':
        return 4
    elif file_type in ('json', 'yaml'):
        return 3
    else:
        return 2


def show_help_level2(file_path: Path) -> int:
    """Показать меню помощи уровня 2 (более настойчивое).

    Args:
        file_path: Путь к файлу, за которым наблюдаем.

    Returns:
        int: Выбор пользователя (1-6).
    """
    console.print()
    console.print(
        Panel(
            "[bold orange]Может, разбить задачу на микрошаг?[/bold orange]\n\n"
            f"Прошло уже 3 минуты. Попробуйте что-то очень простое в [cyan]{file_path.name}[/cyan]:",
            border_style="bright_red",
            padding=(1, 2),
        )
    )

    console.print()
    console.print("[bold white][1][/bold white] Написать TODO")
    console.print("[bold white][2][/bold white] Написать pass")
    console.print("[bold white][3][/bold white] Написать один assert")
    console.print("[bold white][4][/bold white] Открыть README")
    console.print("[bold white][5][/bold white] Запустить таймер")
    console.print("[bold white][6][/bold white] Ничего, продолжу сам")

    console.print()
    choice = IntPrompt.ask("Выберите действие", default=6)

    while choice < 1 or choice > 6:
        console.print("[red]Выберите число от 1 до 6[/red]")
        choice = IntPrompt.ask("Выберите действие", default=6)

    return choice


def apply_help_choice(choice: int, file_path: Path, level: int = 1) -> str:
    """Применить выбор пользователя из меню помощи.

    Args:
        choice: Номер выбранного действия.
        file_path: Путь к файлу.
        level: Уровень помощи (1 или 2).

    Returns:
        str: Описание выполненного действия:
            - "timer" — нужно запустить таймер
            - "skip" — пользователь отказался
            - "text_inserted" — текст вставлен
            - "template:<type>" — шаблон вставлен
            - "open:<path>" — нужно открыть файл
    """
    file_type = _get_file_type(file_path)
    is_test = _is_test_file(file_path)

    if level == 1:
        return _apply_level1_choice(choice, file_path, file_type, is_test)
    else:
        return _apply_level2_choice(choice, file_path)


def _apply_level1_choice(choice: int, file_path: Path, file_type: str, is_test: bool) -> str:
    """Применить выбор уровня 1."""

    if file_type == 'python':
        if is_test:
            if choice == 1:
                return _insert_template(file_path, 'test')
            elif choice == 2:
                return _insert_text(file_path, "\n# TODO: replace with real tests\n")
            elif choice == 3:
                return "timer"
            elif choice == 4:
                return "skip"
        else:
            if choice == 1:
                return _insert_template(file_path, 'function')
            elif choice == 2:
                return _insert_template(file_path, 'class')
            elif choice == 3:
                return _insert_text(file_path, "\n# TODO: add your code here\n")
            elif choice == 4:
                return "timer"
            elif choice == 5:
                return "skip"

    elif file_type == 'markdown':
        if choice == 1:
            return _insert_template(file_path, 'default')
        elif choice == 2:
            return _insert_text(file_path, f"\n# {file_path.stem}\n\n")
        elif choice == 3:
            return "timer"
        elif choice == 4:
            return "skip"

    elif file_type in ('json', 'yaml'):
        if choice == 1:
            return _insert_template(file_path, 'default')
        elif choice == 2:
            return "timer"
        elif choice == 3:
            return "skip"

    else:
        if choice == 1:
            return "timer"
        elif choice == 2:
            return "skip"

    return "skip"


def _apply_level2_choice(choice: int, file_path: Path) -> str:
    """Применить выбор уровня 2."""
    if choice == 1:
        return _insert_text(file_path, "\n# TODO: \n")
    elif choice == 2:
        return _insert_text(file_path, "\npass\n")
    elif choice == 3:
        return _insert_text(file_path, "\nassert True\n")
    elif choice == 4:
        readme = Path("README.md")
        if readme.exists():
            return f"open:{readme}"
        return "skip"
    elif choice == 5:
        return "timer"
    elif choice == 6:
        return "skip"

    return "skip"


def _insert_template(file_path: Path, template_type: str) -> str:
    """Вставить шаблон в файл."""
    template = FileTemplates.get_template(file_path, template_type)

    if template is None:
        console.print(f"[yellow]Шаблон для {file_path.suffix} не найден[/yellow]")
        return "skip"

    try:
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            if content.strip():
                file_path.write_text(content + "\n" + template, encoding='utf-8')
                console.print(f"[green]Шаблон '{template_type}' добавлен в конец файла[/green]")
            else:
                file_path.write_text(template, encoding='utf-8')
                console.print(f"[green]Шаблон '{template_type}' вставлен в пустой файл[/green]")
        else:
            file_path.write_text(template, encoding='utf-8')
            console.print(f"[green]Файл создан с шаблоном '{template_type}'[/green]")

        return f"template:{template_type}"
    except Exception as e:
        console.print(f"[red]Ошибка при вставке шаблона: {e}[/red]")
        return "skip"


def _insert_text(file_path: Path, text: str) -> str:
    """Вставить текст в файл."""
    try:
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            file_path.write_text(content + text, encoding='utf-8')
        else:
            file_path.write_text(text, encoding='utf-8')

        console.print(f"[green]Текст добавлен в файл[/green]")
        return "text_inserted"
    except Exception as e:
        console.print(f"[red]Ошибка при вставке текста: {e}[/red]")
        return "skip"


def show_success_message(file_path: Path, activity_info: dict):
    """Показать сообщение об успешном начале работы."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]Отлично! Работа началась.[/bold green]\n\n"
            f"Файл [cyan]{file_path.name}[/cyan] изменился.\n"
            f"Вы проявили активность — модуль завершает работу.\n\n"
            f"[dim]Продолжайте в том же духе![/dim]",
            border_style="green",
        )
    )