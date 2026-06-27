"""Тесты для core/tracker.py."""

import json
from pathlib import Path

import pytest

from breaker.core.schema import Ritual, RitualResult, ActionType
from breaker.core.tracker import (
    log_ritual_result,
    read_log,
    get_stats,
    clear_log,
)


@pytest.fixture
def success_result():
    ritual = Ritual(
        signal="файл пуст",
        action="написать функцию",
        target="example.py",
        action_type=ActionType.OPEN_FILE,
        task_id="task_123",
    )
    return RitualResult(
        ritual=ritual,
        success=True,
        evidence_link="file:///path/to/example.py",
    )


@pytest.fixture
def error_result():
    ritual = Ritual(
        signal="команда не работает",
        action="проверить синтаксис",
        target="npm test",
        action_type=ActionType.RUN_SHELL,
        task_id="task_456",
    )
    return RitualResult(
        ritual=ritual,
        success=False,
        error_message="Command not found",
    )


@pytest.fixture
def temp_log(tmp_path):
    return str(tmp_path / "test.log")


class TestLogRitualResult:
    def test_creates_log_file(self, success_result, temp_log):
        log_file = log_ritual_result(success_result, log_path=temp_log)
        assert log_file.exists()

    def test_creates_parent_directory(self, success_result, tmp_path):
        nested_log = str(tmp_path / "nested" / "dir" / "test.log")
        log_file = log_ritual_result(success_result, log_path=nested_log)
        assert log_file.exists()

    def test_writes_valid_json(self, success_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)

        with open(temp_log, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline().strip())

        assert entry["signal"] == "файл пуст"
        assert entry["action"] == "написать функцию"
        assert entry["target"] == "example.py"
        assert entry["action_type"] == "open_file"
        assert entry["task_id"] == "task_123"
        assert entry["success"] is True
        assert entry["evidence_link"] == "file:///path/to/example.py"
        assert "timestamp" in entry
        assert entry["event_type"] == "ritual_completed"

    def test_writes_error_result(self, error_result, temp_log):
        log_ritual_result(error_result, log_path=temp_log)

        with open(temp_log, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline().strip())

        assert entry["success"] is False
        assert entry["error_message"] == "Command not found"

    def test_appends_multiple_entries(self, success_result, error_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)
        log_ritual_result(error_result, log_path=temp_log)
        log_ritual_result(success_result, log_path=temp_log)

        with open(temp_log, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]

        assert len(lines) == 3

    def test_custom_event_type(self, success_result, temp_log):
        log_ritual_result(
            success_result,
            log_path=temp_log,
            event_type="plan_created",
        )

        with open(temp_log, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline().strip())

        assert entry["event_type"] == "plan_created"

    def test_handles_russian_text(self, temp_log):
        ritual = Ritual(
            signal="открываю проект",
            action="запускаю тесты",
            target="main.py",
            action_type=ActionType.RUN_SHELL,
        )
        result = RitualResult(ritual=ritual, success=True)
        log_ritual_result(result, log_path=temp_log)

        with open(temp_log, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline().strip())

        assert entry["signal"] == "открываю проект"


class TestReadLog:
    def test_read_empty_log(self, temp_log):
        assert read_log(temp_log) == []

    def test_read_single_entry(self, success_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)
        entries = read_log(temp_log)

        assert len(entries) == 1
        assert entries[0]["signal"] == "файл пуст"

    def test_read_multiple_entries(self, success_result, error_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)
        log_ritual_result(error_result, log_path=temp_log)

        entries = read_log(temp_log)
        assert len(entries) == 2
        assert entries[0]["success"] is True
        assert entries[1]["success"] is False

    def test_skips_invalid_lines(self, success_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)

        with open(temp_log, "a", encoding="utf-8") as f:
            f.write("invalid json line\n")

        log_ritual_result(success_result, log_path=temp_log)

        entries = read_log(temp_log)
        assert len(entries) == 2


class TestGetStats:
    def test_empty_log_stats(self, temp_log):
        stats = get_stats(temp_log)
        assert stats["total"] == 0
        assert stats["success_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["action_types"] == {}

    def test_stats_with_entries(self, success_result, error_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)
        log_ritual_result(success_result, log_path=temp_log)
        log_ritual_result(error_result, log_path=temp_log)

        stats = get_stats(temp_log)

        assert stats["total"] == 3
        assert stats["success_count"] == 2
        assert stats["fail_count"] == 1
        assert abs(stats["success_rate"] - 2 / 3) < 0.01
        assert stats["action_types"]["open_file"] == 2
        assert stats["action_types"]["run_shell"] == 1

    def test_stats_all_success(self, success_result, temp_log):
        for _ in range(5):
            log_ritual_result(success_result, log_path=temp_log)

        stats = get_stats(temp_log)
        assert stats["success_rate"] == 1.0
        assert stats["fail_count"] == 0


class TestClearLog:
    def test_clear_existing_log(self, success_result, temp_log):
        log_ritual_result(success_result, log_path=temp_log)
        assert Path(temp_log).exists()

        clear_log(temp_log)
        assert not Path(temp_log).exists()

    def test_clear_nonexistent_log(self, temp_log):
        clear_log(temp_log)
        assert not Path(temp_log).exists()
