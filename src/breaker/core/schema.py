"""Схема данных для White-sheet-breaker."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ActionType(Enum):
    """Типы действий модуля."""

    OPEN_FILE = "open_file"

    CREATE_TEST = "create_test"


class EventType(Enum):
    """Типы xAPI-событий."""

    TASK_STARTED = "task_started"
    PLAN_CREATED = "plan_created"


@dataclass
class Ritual:
    """Правило «если-то» для начала задачи."""

    signal: str
    action: str
    target: str
    action_type: ActionType
    task_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        data = asdict(self)
        data["action_type"] = self.action_type.value
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "Ritual":
        data = data.copy()
        data["action_type"] = ActionType(data["action_type"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "Ritual":
        return cls.from_dict(json.loads(json_str))

    def format_rule(self) -> str:
        return f"ЕСЛИ {self.signal} → ТО {self.action}"

    def validate(self) -> list[str]:
        errors = []
        if not self.signal.strip():
            errors.append("Сигнал не может быть пустым")
        if not self.action.strip():
            errors.append("Действие не может быть пустым")
        if not self.target.strip():
            errors.append("Цель не может быть пустой")
        if not isinstance(self.action_type, ActionType):
            errors.append(f"Невалидный тип действия: {self.action_type}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass
class RitualResult:
    """Результат выполнения ритуала."""

    ritual: Ritual
    success: bool
    evidence_link: Optional[str] = None
    error_message: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ritual": self.ritual.to_dict(),
            "success": self.success,
            "evidence_link": self.evidence_link,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def mark_finished(self) -> None:
        self.finished_at = datetime.now().isoformat()


@dataclass
class XapiActor:
    """Актор xAPI-стейтмента (ученик)."""

    mbox: str
    name: str

    def to_dict(self) -> dict:
        return {"mbox": self.mbox, "name": self.name}


@dataclass
class XapiVerb:
    """Глагол xAPI-стейтмента."""

    id: str
    display: dict[str, str] = field(default_factory=lambda: {"en-US": "launched"})

    def to_dict(self) -> dict:
        return {"id": self.id, "display": self.display}

    @classmethod
    def launched(cls) -> "XapiVerb":
        return cls(
            id="http://adlnet.gov/expapi/verbs/launched",
            display={"en-US": "launched", "ru-RU": "начал"},
        )

    @classmethod
    def planned(cls) -> "XapiVerb":
        return cls(
            id="http://adlnet.gov/expapi/verbs/planned",
            display={"en-US": "planned", "ru-RU": "запланировал"},
        )


@dataclass
class XapiObject:
    """Объект xAPI-стейтмента (задача)."""

    id: str
    definition: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "definition": self.definition}

    @classmethod
    def from_task(cls, task_id: str, task_name: str) -> "XapiObject":
        return cls(
            id=f"task:{task_id}",
            definition={"name": {"en-US": task_name}},
        )


@dataclass
class XapiContext:
    """Контекст xAPI-стейтмента (курс, навык)."""

    course_id: Optional[str] = None
    skill_id: Optional[str] = None

    def to_dict(self) -> dict:
        context: dict[str, Any] = {}
        if self.course_id:
            context["contextActivities"] = {"parent": [{"id": f"course:{self.course_id}"}]}
        if self.skill_id:
            context.setdefault("extensions", {})
            context["extensions"]["skill:id"] = self.skill_id
        return context


@dataclass
class XapiStatement:
    """Полный xAPI-стейтмент по стандарту ADL."""

    actor: XapiActor
    verb: XapiVerb
    object: XapiObject
    result: dict[str, Any]
    context: Optional[XapiContext] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        statement = {
            "actor": self.actor.to_dict(),
            "verb": self.verb.to_dict(),
            "object": self.object.to_dict(),
            "result": self.result,
            "timestamp": self.timestamp,
        }
        if self.context:
            ctx_dict = self.context.to_dict()
            if ctx_dict:
                statement["context"] = ctx_dict
        return statement

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_ritual_result(
        cls,
        result: RitualResult,
        actor: XapiActor,
        course_id: Optional[str] = None,
        event_type: EventType = EventType.TASK_STARTED,
    ) -> "XapiStatement":
        """Создать xAPI-стейтмент из результата выполнения ритуала."""
        ritual = result.ritual

        verb = XapiVerb.launched() if event_type == EventType.TASK_STARTED else XapiVerb.planned()

        task_id = ritual.task_id or "unknown"
        obj = XapiObject.from_task(task_id, ritual.signal)

        result_dict: dict[str, Any] = {
            "success": result.success,
            "response": ritual.format_rule(),
            "extensions": {
                "ifThenRule": ritual.to_json(indent=None),
                "actionType": ritual.action_type.value,
                "target": ritual.target,
            },
        }
        if result.evidence_link:
            result_dict["extensions"]["evidenceLink"] = result.evidence_link
        if result.error_message:
            result_dict["extensions"]["errorMessage"] = result.error_message

        context = XapiContext(course_id=course_id) if course_id else None

        return cls(
            actor=actor,
            verb=verb,
            object=obj,
            result=result_dict,
            context=context,
            timestamp=result.started_at,
        )
