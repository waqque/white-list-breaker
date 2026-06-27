"""Логирование результатов ритуалов в NDJSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from breaker.core.schema import RitualResult

DEFAULT_LOG_PATH = "logs/breaker.log"


def log_ritual_result(
    result: RitualResult,
    log_path: str = DEFAULT_LOG_PATH,
    event_type: str = "ritual_completed",
) -> Path:
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "task_id": result.ritual.task_id,
        "signal": result.ritual.signal,
        "action": result.ritual.action,
        "target": result.ritual.target,
        "action_type": result.ritual.action_type.value,
        "success": result.success,
        "evidence_link": result.evidence_link,
        "error_message": result.error_message,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return log_file


def read_log(log_path: str = DEFAULT_LOG_PATH) -> list[dict]:
    log_file = Path(log_path)
    if not log_file.exists():
        return []

    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def get_stats(log_path: str = DEFAULT_LOG_PATH) -> dict:
    entries = read_log(log_path)

    if not entries:
        return {
            "total": 0,
            "success_count": 0,
            "fail_count": 0,
            "success_rate": 0.0,
            "action_types": {},
        }

    success_count = sum(1 for e in entries if e.get("success"))
    fail_count = len(entries) - success_count

    action_types: dict[str, int] = {}
    for e in entries:
        at = e.get("action_type", "unknown")
        action_types[at] = action_types.get(at, 0) + 1

    return {
        "total": len(entries),
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_count / len(entries),
        "action_types": action_types,
    }


def clear_log(log_path: str = DEFAULT_LOG_PATH) -> None:
    log_file = Path(log_path)
    if log_file.exists():
        log_file.unlink()
