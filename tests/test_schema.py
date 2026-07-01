"""Тесты для core/schema.py."""

import json
import pytest
from breaker.core.schema import (
    Ritual,
    RitualResult,
    ActionType,
    EventType,
    XapiActor,
    XapiVerb,
    XapiObject,
    XapiContext,
    XapiStatement,
)


class TestActionType:
    def test_enum_values(self):
        assert ActionType.OPEN_FILE.value == "open_file"
        assert ActionType.CREATE_TEST.value == "create_test"

    def test_enum_from_string(self):
        assert ActionType("open_file") == ActionType.OPEN_FILE


class TestRitual:
    def test_create_ritual(self):
        ritual = Ritual(
            signal="файл пуст",
            action="написать шаблон функции",
            target="example.py",
            action_type=ActionType.OPEN_FILE,
        )
        assert ritual.signal == "файл пуст"
        assert ritual.action == "написать шаблон функции"
        assert ritual.target == "example.py"
        assert ritual.action_type == ActionType.OPEN_FILE
        assert ritual.task_id is None
        assert ritual.created_at

    def test_create_ritual_with_task_id(self):
        ritual = Ritual(
            signal="открываю проект",
            action="открываю файл",
            target="main.py",
            action_type=ActionType.OPEN_FILE,
            task_id="task_123",
        )

    def test_format_rule(self):
        ritual = Ritual(
            signal="файл пуст",
            action="написать функцию",
            target="main.py",
            action_type=ActionType.OPEN_FILE,
        )
        assert ritual.format_rule() == "ЕСЛИ файл пуст → ТО написать функцию"

    def test_to_dict(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.CREATE_TEST,
            task_id="task_456",
        )
        data = ritual.to_dict()
        assert data["signal"] == "сигнал"
        assert data["action_type"] == "create_test"
        assert data["task_id"] == "task_456"
        assert "created_at" in data

    def test_to_json(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        json_str = ritual.to_json()
        assert "сигнал" in json_str
        assert "open_file" in json_str

    def test_from_dict(self):
        data = {
            "signal": "файл пуст",
            "action": "написать функцию",
            "target": "main.py",
            "action_type": "open_file",
            "task_id": "task_789",
            "created_at": "2026-06-24T10:00:00",
        }
        ritual = Ritual.from_dict(data)
        assert ritual.signal == "файл пуст"
        assert ritual.action_type == ActionType.OPEN_FILE
        assert ritual.task_id == "task_789"

    def test_from_json(self):
        json_str = """
        {
            "signal": "тест",
            "action": "действие",
            "target": "цель",
            "action_type": "open_file",
            "task_id": null,
            "created_at": "2026-06-24T10:00:00"
        }
        """
        ritual = Ritual.from_json(json_str)

    def test_roundtrip_json(self):
        original = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.CREATE_TEST,
            task_id="task_001",
        )
        json_str = original.to_json()
        restored = Ritual.from_json(json_str)
        assert restored.signal == original.signal
        assert restored.action_type == original.action_type
        assert restored.task_id == original.task_id

    def test_validate_empty_signal(self):
        ritual = Ritual(
            signal="",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        errors = ritual.validate()
        assert len(errors) > 0
        assert any("Сигнал" in e for e in errors)

    def test_validate_empty_action(self):
        ritual = Ritual(
            signal="сигнал",
            action="",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        errors = ritual.validate()
        assert any("Действие" in e for e in errors)

    def test_validate_empty_target(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="",
            action_type=ActionType.OPEN_FILE,
        )
        errors = ritual.validate()
        assert any("Цель" in e for e in errors)

    def test_validate_ok(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        assert ritual.validate() == []
        assert ritual.is_valid() is True

    def test_invalid_action_type(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type="invalid",
        )
        errors = ritual.validate()
        assert any("Невалидный" in e for e in errors)


class TestRitualResult:
    def test_success_result(self):
        ritual = Ritual(
            signal="файл пуст",
            action="написать функцию",
            target="main.py",
            action_type=ActionType.OPEN_FILE,
        )
        result = RitualResult(
            ritual=ritual,
            success=True,
            evidence_link="file:///path/to/main.py",
        )
        assert result.success is True
        assert result.evidence_link == "file:///path/to/main.py"
        assert result.error_message is None
        assert result.started_at

    def test_error_result(self):
        ritual = Ritual(
            signal="файл не найден",
            action="проверить путь",
            target="missing.py",
            action_type=ActionType.OPEN_FILE,
        )

    def test_to_dict(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        result = RitualResult(ritual=ritual, success=True)
        data = result.to_dict()
        assert data["success"] is True
        assert "ritual" in data
        assert data["ritual"]["signal"] == "сигнал"

    def test_to_json(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        result = RitualResult(ritual=ritual, success=True)
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True

    def test_mark_finished(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        result = RitualResult(ritual=ritual, success=True)
        assert result.finished_at is None
        result.mark_finished()
        assert result.finished_at is not None


class TestXapiActor:
    def test_actor_creation(self):
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")
        data = actor.to_dict()
        assert data["mbox"] == "mailto:student@example.com"
        assert data["name"] == "Student"


class TestXapiVerb:
    def test_verb_launched(self):
        verb = XapiVerb.launched()
        data = verb.to_dict()
        assert data["id"] == "http://adlnet.gov/expapi/verbs/launched"
        assert "ru-RU" in data["display"]

    def test_verb_planned(self):
        verb = XapiVerb.planned()
        data = verb.to_dict()
        assert data["id"] == "http://adlnet.gov/expapi/verbs/planned"


class TestXapiObject:
    def test_object_from_task(self):
        obj = XapiObject.from_task("123", "Задача 123")
        data = obj.to_dict()
        assert data["id"] == "task:123"
        assert data["definition"]["name"]["en-US"] == "Задача 123"


class TestXapiContext:
    def test_context_with_course(self):
        ctx = XapiContext(course_id="CS101")
        data = ctx.to_dict()
        assert "contextActivities" in data
        assert data["contextActivities"]["parent"][0]["id"] == "course:CS101"

    def test_context_with_skill(self):
        ctx = XapiContext(skill_id="SKILL_001")
        data = ctx.to_dict()
        assert "extensions" in data
        assert data["extensions"]["skill:id"] == "SKILL_001"

    def test_empty_context(self):
        ctx = XapiContext()
        data = ctx.to_dict()
        assert data == {}


class TestXapiStatement:
    def _make_ritual_result(self):
        ritual = Ritual(
            signal="файл example.py пуст",
            action="напишу шаблон функции",
            target="example.py",
            action_type=ActionType.OPEN_FILE,
            task_id="123",
        )
        return RitualResult(
            ritual=ritual,
            success=True,
            evidence_link="file:///path/to/example.py",
        )

    def test_statement_from_ritual_result(self):
        result = self._make_ritual_result()
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")

        statement = XapiStatement.from_ritual_result(
            result=result,
            actor=actor,
            course_id="CS101",
            event_type=EventType.TASK_STARTED,
        )

        data = statement.to_dict()

        assert data["actor"]["mbox"] == "mailto:student@example.com"
        assert data["verb"]["id"] == "http://adlnet.gov/expapi/verbs/launched"
        assert data["object"]["id"] == "task:123"
        assert data["result"]["success"] is True
        assert "ЕСЛИ" in data["result"]["response"]
        assert data["result"]["extensions"]["evidenceLink"] == "file:///path/to/example.py"
        assert "ifThenRule" in data["result"]["extensions"]
        assert data["context"]["contextActivities"]["parent"][0]["id"] == "course:CS101"
        assert "timestamp" in data

    def test_statement_without_context(self):
        result = self._make_ritual_result()
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")

        statement = XapiStatement.from_ritual_result(
            result=result,
            actor=actor,
        )

        data = statement.to_dict()
        assert "context" not in data

    def test_statement_planned_event(self):
        result = self._make_ritual_result()
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")

        statement = XapiStatement.from_ritual_result(
            result=result,
            actor=actor,
            event_type=EventType.PLAN_CREATED,
        )

        data = statement.to_dict()
        assert data["verb"]["id"] == "http://adlnet.gov/expapi/verbs/planned"

    def test_statement_with_error(self):
        ritual = Ritual(
            signal="файл не найден",
            action="проверить путь",
            target="missing.py",
            action_type=ActionType.OPEN_FILE,
            task_id="456",
        )
    
    def test_statement_to_json(self):
        result = self._make_ritual_result()
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")

        statement = XapiStatement.from_ritual_result(
            result=result,
            actor=actor,
            course_id="CS101",
        )

        json_str = statement.to_json()
        parsed = json.loads(json_str)
        assert parsed["actor"]["name"] == "Student"
        assert parsed["object"]["id"] == "task:123"

    def test_statement_unknown_task_id(self):
        ritual = Ritual(
            signal="сигнал",
            action="действие",
            target="цель",
            action_type=ActionType.OPEN_FILE,
        )
        result = RitualResult(ritual=ritual, success=True)
        actor = XapiActor(mbox="mailto:student@example.com", name="Student")

        statement = XapiStatement.from_ritual_result(
            result=result,
            actor=actor,
        )

        data = statement.to_dict()
        assert data["object"]["id"] == "task:unknown"
