"""Кастомные исключения для engine."""


class EngineError(Exception):
    """Базовое исключение для всех ошибок engine."""

    pass


class BreakerFileNotFoundError(EngineError):
    """Файл не найден."""

    pass


class CommandNotFoundError(EngineError):
    """Команда не найдена в системе."""

    pass


class CommandTimeoutError(EngineError):
    """Команда не успела выполниться за отведённое время."""

    pass


class CommandFailedError(EngineError):
    """Команда завершилась с ненулевым кодом возврата."""

    def __init__(self, returncode: int, stderr: str):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command failed with code {returncode}: {stderr}")
