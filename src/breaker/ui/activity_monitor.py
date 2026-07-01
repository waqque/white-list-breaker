"""Мониторинг активности пользователя.

Наблюдает за изменением файлов после выполнения микро-шага.
Если пользователь неактивен — показывает меню помощи через колбэки.
Если пользователь начал работать — завершает наблюдение.

Реализует конечный автомат состояний:
    IDLE -> HELP_LEVEL_1 -> HELP_LEVEL_2 -> TIMEOUT
      ↓           ↓              ↓
    ACTIVE    ACTIVE         ACTIVE
      ↓           ↓              ↓
    SUCCESS   SUCCESS        SUCCESS

Интеграция:
- main.py: создаёт ActivityMonitor и передаёт колбэки
- help_menu.py: предоставляет функции для колбэков
"""

import time
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel

console = Console()


class ActivityMonitor:
    """Мониторинг активности пользователя по изменению файлов."""

    def __init__(
        self,
        watched_files: list[Path],
        idle_threshold_level1: int = 60,
        idle_threshold_level2: int = 180,
        idle_threshold_timeout: int = 300,
        activity_threshold: int = 100,
        check_interval: int = 10,
        help_level1_callback: Optional[Callable] = None,
        help_level2_callback: Optional[Callable] = None,
        apply_choice_callback: Optional[Callable] = None,
        success_callback: Optional[Callable] = None,
        progress_refresh_callback: Optional[Callable] = None,
    ):
        """
        Args:
            watched_files: Список файлов для отслеживания изменений.
            idle_threshold_level1: Секунды бездействия до меню уровня 1.
            idle_threshold_level2: Секунды бездействия до меню уровня 2.
            idle_threshold_timeout: Секунды бездействия до завершения сессии.
            activity_threshold: Количество новых символов для определения активности.
            check_interval: Интервал проверки в секундах.
            help_level1_callback: Функция для показа меню уровня 1. Возвращает int (выбор).
            help_level2_callback: Функция для показа меню уровня 2. Возвращает int (выбор).
            apply_choice_callback: Функция для применения выбора. Принимает (choice, level), возвращает str.
            success_callback: Функция для показа сообщения об успехе. Принимает dict с инфо об активности.
            progress_refresh_callback: Функция для приостановки/возобновления обновления прогресса.
        """
        self.watched_files = watched_files
        self.idle_threshold_level1 = idle_threshold_level1
        self.idle_threshold_level2 = idle_threshold_level2
        self.idle_threshold_timeout = idle_threshold_timeout
        self.activity_threshold = activity_threshold
        self.check_interval = check_interval

        self.help_level1_callback = help_level1_callback
        self.help_level2_callback = help_level2_callback
        self.apply_choice_callback = apply_choice_callback
        self.success_callback = success_callback
        self.progress_refresh_callback = progress_refresh_callback

        self.running = False
        self.help_level = 0
        self.last_activity_time = time.time()
        self.session_start_time = time.time()
        self.baseline_sizes = self._get_file_sizes()
        self.help_count = 0
        self.pending_action = False
        self.interrupted = False

    def _get_file_sizes(self) -> dict[Path, int]:
        """Получить текущие размеры отслеживаемых файлов."""
        sizes = {}
        for file_path in self.watched_files:
            if file_path.exists():
                sizes[file_path] = file_path.stat().st_size
            else:
                sizes[file_path] = 0
        return sizes

    def _get_activity_info(self) -> dict:
        """Получить информацию об активности."""
        current_sizes = self._get_file_sizes()
        total_chars_added = 0
        changed_files = []

        for file_path in self.watched_files:
            current_size = current_sizes.get(file_path, 0)
            baseline_size = self.baseline_sizes.get(file_path, 0)
            diff = current_size - baseline_size
            total_chars_added += diff
            if diff > 0:
                changed_files.append({
                    "path": str(file_path),
                    "chars_added": diff,
                })

        return {
            "total_chars_added": total_chars_added,
            "changed_files": changed_files,
            "session_duration": time.time() - self.session_start_time,
            "help_count": self.help_count,
        }

    def _check_activity(self) -> bool:
        """Проверить, была ли достаточная активность."""
        info = self._get_activity_info()
        return info["total_chars_added"] >= self.activity_threshold

    def _check_file_modified(self) -> bool:
        """Проверить, был ли файл изменён хотя бы немного."""
        current_sizes = self._get_file_sizes()
        for file_path in self.watched_files:
            current_size = current_sizes.get(file_path, 0)
            baseline_size = self.baseline_sizes.get(file_path, 0)
            if current_size != baseline_size:
                return True
        return False

    def _pause_progress(self):
        """Приостановить обновление прогресса."""
        if self.progress_refresh_callback:
            try:
                self.progress_refresh_callback(True)
            except Exception:
                pass

    def _resume_progress(self):
        """Возобновить обновление прогресса."""
        if self.progress_refresh_callback:
            try:
                self.progress_refresh_callback(False)
            except Exception:
                pass

    def _show_help_menu_safe(self, level: int) -> str:
        """Показать меню помощи безопасно (с приостановкой прогресса)."""
        self._pause_progress()
        
        try:
            console.print()
            console.print(
                Panel(
                    "[bold yellow]Помощь при бездействии[/bold yellow]",
                    border_style="yellow",
                )
            )
            
            if level == 1:
                if self.help_level1_callback:
                    choice = self.help_level1_callback()
                else:
                    from breaker.ui.help_menu import show_help_level1
                    choice = show_help_level1(self.watched_files[0])
            else:
                if self.help_level2_callback:
                    choice = self.help_level2_callback()
                else:
                    from breaker.ui.help_menu import show_help_level2
                    choice = show_help_level2(self.watched_files[0])
            
            if self.apply_choice_callback:
                result = self.apply_choice_callback(choice, level=level)
            else:
                result = "skip"
                
            return result
            
        finally:
            self._resume_progress()
            console.print()

    def _handle_help_level1(self) -> str:
        """Показать меню уровня 1 и обработать выбор."""
        self.help_count += 1
        self.help_level = 1
        return self._show_help_menu_safe(1)

    def _handle_help_level2(self) -> str:
        """Показать меню уровня 2 и обработать выбор."""
        self.help_count += 1
        self.help_level = 2
        return self._show_help_menu_safe(2)

    def _handle_success(self):
        """Показать сообщение об успехе."""
        info = self._get_activity_info()
        if self.success_callback:
            self.success_callback(info)

    def _process_help_result(self, result: str):
        """Обработать результат выбора из меню помощи."""
        if result == "timer":
            console.print("\n[bold cyan]Запуск Pomodoro-таймера...[/bold cyan]")
            try:
                from breaker.ui.timer import run_timer_with_prompt
                run_timer_with_prompt()
            except KeyboardInterrupt:
                console.print("\n[yellow]Таймер прерван пользователем.[/yellow]")
                self.interrupted = True
            except Exception as e:
                console.print(f"[yellow]Ошибка таймера: {e}[/yellow]")
            self.pending_action = False

        elif result.startswith("open:"):
            file_to_open = Path(result.split(":", 1)[1])
            console.print(f"[dim]Открываю {file_to_open}...[/dim]")
            try:
                from breaker.engine.executor import open_file
                open_file(file_to_open)
                console.print(f"[green]Файл {file_to_open} открыт[/green]")
            except Exception as e:
                console.print(f"[yellow]Не удалось открыть файл: {e}[/yellow]")
            self.pending_action = False

        elif result in ("text_inserted", "skip"):
            self.pending_action = True

        elif result.startswith("template:"):
            self.pending_action = True

    def set_interrupted(self):
        """Установить флаг прерывания."""
        self.interrupted = True
        self.running = False

    def start_monitoring(self) -> str:
        """Запустить мониторинг активности.
        
        Returns:
            str: "success" — пользователь начал работать,
                "inactive" — сессия завершена из-за неактивности,
                "interrupted" — прерван пользователем,
                "stopped" — мониторинг остановлен вручную.
        """
        self.running = True
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        self.baseline_sizes = self._get_file_sizes()
        self.help_level = 0
        self.help_count = 0
        self.pending_action = False
        self.interrupted = False

        console.print()
        console.print(
            f"[dim]Отслеживаю {len(self.watched_files)} файл(ов). "
        )
        for f in self.watched_files:
            console.print(f"[dim]  -> {f}[/dim]")
        console.print()
        console.print()

        try:
            while self.running:
                if self.interrupted:
                    return "interrupted"

                if self._check_activity():
                    self._handle_success()
                    return "success"

                idle_time = time.time() - self.last_activity_time

                # Уровень 1: первое напоминание
                if self.help_level == 0 and idle_time >= self.idle_threshold_level1:
                    result = self._handle_help_level1()
                    self._process_help_result(result)

                    if self.interrupted:
                        return "interrupted"

                    if self.pending_action:
                        self.baseline_sizes = self._get_file_sizes()
                        self.last_activity_time = time.time()
                        # help_level остается 1 (установлено в _handle_help_level1)
                        self.pending_action = False
                        continue
                    elif result == "timer":
                        self.last_activity_time = time.time()
                        # help_level остается 1
                        continue

                # Уровень 2: второе напоминание
                elif self.help_level == 1 and idle_time >= self.idle_threshold_level2:

                    result = self._handle_help_level2()
                    self._process_help_result(result)

                    if self.interrupted:
                        return "interrupted"

                    if self.pending_action:
                        self.baseline_sizes = self._get_file_sizes()
                        self.last_activity_time = time.time()
                        # help_level остается 2 (установлено в _handle_help_level2)
                        self.pending_action = False
                        continue
                    elif result == "timer":
                        self.last_activity_time = time.time()
                        # help_level остается 2
                        continue

                # Таймаут: слишком долго без активности
                elif self.help_level >= 1 and idle_time >= self.idle_threshold_timeout:
                    console.print()
                    console.print(
                        f"[yellow]Сессия завершена из-за длительного бездействия ({int(idle_time)} сек).[/yellow]"
                    )
                    return "inactive"

                # Проверяем изменения файла (пользователь начал работать)
                if self._check_file_modified():
                    current_sizes = self._get_file_sizes()
                    total_diff = sum(
                        current_sizes.get(f, 0) - self.baseline_sizes.get(f, 0)
                        for f in self.watched_files
                    )
                    # Если изменения есть, но меньше порога — это ручная активность
                    if 0 < total_diff < self.activity_threshold:
                        console.print(f"[dim]Обнаружены изменения ({total_diff} символов)[/dim]")
                        self.last_activity_time = time.time()
                        # Сбрасываем уровень помощи, потому что пользователь начал работать
                        self.help_level = 0
                        # Обновляем baseline
                        self.baseline_sizes = self._get_file_sizes()
                        # Проверяем, не набралось ли достаточно
                        if self._check_activity():
                            self._handle_success()
                            return "success"

                # Ждём перед следующей проверкой
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            return "interrupted"

        return "stopped"

    def stop_monitoring(self):
        """Остановить мониторинг."""
        self.running = False