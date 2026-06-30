# Помодоро-таймер с выбором длительности пользователем.
# После подтверждения правила «если–то» пользователь сам выбирает, сколько минут работать.
# Таймер помогает сосредоточиться и не отвлекаться.

import os
import time
import subprocess
import sys
from pathlib import Path
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt

console = Console()


def _format_seconds(seconds: int) -> str:
    # Форматировать секунды в MM:SS
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _is_wsl() -> bool:
    # Определить, запущен ли код в WSL (Windows Subsystem for Linux)
    # переменная окружения WSL_DISTRO_NAME
    if os.environ.get("WSL_DISTRO_NAME"):
        return True

    # /proc/version содержит "Microsoft" или "WSL"
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            version = f.read().lower()
            if "microsoft" in version or "wsl" in version:
                return True
    except (OSError, IOError):
        pass

    return False


def _linux_path_to_windows(linux_path: Path) -> str:
    """Конвертировать Linux-путь (/mnt/c/...) в Windows-путь (C:\\...)."""
    from pathlib import PurePosixPath

    # Пробуем wslpath
    try:
        result = subprocess.run(
            ["wslpath", "-w", str(linux_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # Fallback: ручная конвертация
    # Используем PurePosixPath для парсинга, но as_posix() для строки
    posix_path = PurePosixPath(linux_path)
    path_str = posix_path.as_posix()  # ← ИСПРАВЛЕНО: используем as_posix()

    if path_str.startswith("/mnt/"):
        drive_letter = path_str[5].upper()
        rest = path_str[7:]
        windows_path = f"{drive_letter}:\\{rest.replace('/', chr(92))}"
        return windows_path

    return path_str


def _play_sound() -> None:
    """Воспроизвести звуковой сигнал (кроссплатформенно, включая WSL)."""
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    sound_path = base_dir / "data" / "sounds" / "wow-sound-effect.wav"

    # Проверка на WSL — используем Windows-механизмы
    if _is_wsl():
        _play_sound_wsl(sound_path)
        return

    try:
        if sound_path.exists():
            if sys.platform == "darwin":  # macOS
                subprocess.run(
                    ["afplay", str(sound_path)],
                    capture_output=True,
                    timeout=10,
                )
            elif sys.platform == "win32":  # Windows
                # Используем PowerShell с SoundPlayer (надёжнее для WAV)
                subprocess.run(
                    [
                        "powershell",
                        "-c",
                        f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()',
                    ],
                    capture_output=True,
                    timeout=10,
                )
            else:  # Linux
                for player in ["paplay", "mpv", "ffplay", "aplay"]:
                    try:
                        subprocess.run(
                            [player, str(sound_path)],
                            capture_output=True,
                            timeout=10,
                        )
                        return
                    except FileNotFoundError:
                        continue
        else:
            console.print(f"[yellow]Звуковой файл не найден: {sound_path}[/yellow]")
            _play_system_sound()
    except Exception as e:
        console.print(f"[dim]Ошибка воспроизведения: {e}[/dim]")
        # Fallback на системный звук
        _play_system_sound()


def _play_sound_wsl(sound_path: Path) -> None:
    """Воспроизвести звук в WSL через Windows PowerShell."""
    try:
        # Конвертируем Linux-путь в Windows-путь
        if sound_path.exists():
            windows_path = _linux_path_to_windows(sound_path)
            # Экранируем обратные слеши для PowerShell
            windows_path_escaped = windows_path.replace("\\", "\\\\")

            # Вызываем powershell.exe (он доступен из WSL!)
            subprocess.run(
                [
                    "powershell.exe",
                    "-c",
                    f'(New-Object Media.SoundPlayer "{windows_path_escaped}").PlaySync()',
                ],
                capture_output=True,
                timeout=10,
            )
            return
        else:
            console.print(f"[yellow]Звуковой файл не найден: {sound_path}[/yellow]")
            _play_system_sound_wsl()
    except Exception as e:
        console.print(f"[dim]Ошибка воспроизведения в WSL: {e}[/dim]")
        _play_system_sound_wsl()


def _play_system_sound() -> None:
    # Воспроизвести системный звук ОС (если свой не найден)
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                capture_output=True,
                timeout=5,
            )
        elif sys.platform == "win32":
            import winsound

            winsound.Beep(1000, 500)
        else:
            print("\a", end="", flush=True)
    except Exception:
        print("\a", end="", flush=True)


def _play_system_sound_wsl() -> None:
    """Системный звук в WSL через Windows."""
    try:
        # Используем стандартный Windows beep через PowerShell
        subprocess.run(
            ["powershell.exe", "-c", "[Console]::Beep(1000, 500)"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        # Последний fallback — bell символ
        print("\a", end="", flush=True)


def ask_duration(default_minutes: int = 5) -> int:
    # Спросить у пользователя, сколько минут работать
    console.print()
    console.print("[bold cyan]Сколько минут будем работать?[/bold cyan]")
    console.print("[dim]Рекомендации:[/dim]")
    console.print("  • [green]5 мин[/green]  — быстрый старт")
    console.print("  • [green]15 мин[/green] — стандартное помодоро")
    console.print("  • [green]25 мин[/green] — классическое помодоро")
    console.print("  • [green]45 мин[/green] — глубокая работа")

    while True:
        try:
            minutes = IntPrompt.ask(
                "\n[yellow]Количество минут[/yellow]",
                default=default_minutes,
            )

            if minutes < 1:
                console.print("[red]Минимум 1 минута.[/red]")
                continue
            if minutes > 50:
                console.print("[red]Максимум 50 минут.[/red]")
                continue

            return minutes

        except (ValueError, KeyboardInterrupt):
            console.print("\n[yellow]Используйте целое число.[/yellow]")


def pomodoro_timer(minutes: int = 5) -> bool:
    # Запустить помодоро-таймер с обратным отсчётом
    total_seconds = minutes * 60

    console.print()
    console.print(
        f"[bold cyan]Запускаем помодоро на {minutes} мин "
        f"({_format_seconds(total_seconds)})[/bold cyan]"
    )
    console.print("[dim]Сосредоточься на задаче. Чтобы прервать — Ctrl+C.[/dim]")
    console.print()

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=1,
    ) as progress:
        task = progress.add_task(
            f"Работаем... ({_format_seconds(total_seconds)})",
            total=total_seconds,
        )

        try:
            for remaining in range(total_seconds, 0, -1):
                progress.update(
                    task,
                    description=f"Осталось: {_format_seconds(remaining)}",
                )
                time.sleep(1)
                progress.update(task, advance=1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Таймер прерван пользователем.[/yellow]")
            return False

    progress.update(task, description="Готово!", completed=total_seconds)

    console.print()
    console.print("[bold green]Время вышло! Отличная работа![/bold green]")

    _play_sound()

    console.print(
        Panel(
            "[bold green]ВРЕМЯ ВЫШЛО![/bold green]\n\n"
            "[dim]Микро-шаг выполнен. Отдохни 5 минут.[/dim]",
            border_style="green",
            title="Pomodoro",
        )
    )

    return True


def run_timer_with_prompt() -> bool:
    # Полный цикл: спросить минуты -> запустить таймер
    console.print(
        Panel(
            "[bold cyan]Помодоро-таймер[/bold cyan]\n\n"
            "Выбери, сколько минут хочешь работать без отвлечений.",
            title="Настройка таймера",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    minutes = ask_duration()
    console.print(f"\n[green]Запускаем таймер на {minutes} мин[/green]")
    return pomodoro_timer(minutes)


if __name__ == "__main__":
    # При прямом запуске — спрашиваем минуты и запускаем таймер
    run_timer_with_prompt()
