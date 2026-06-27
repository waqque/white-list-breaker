"""Тесты для storage/templates.py.

Проверяют:
- Создание и сериализацию RuleTemplate
- Загрузку системных шаблонов из JSON
- CRUD для пользовательских шаблонов
- Защиту системных шаблонов от удаления/перезаписи
- Поиск шаблонов по названию/описанию
- Сортировку списка шаблонов

Все тесты изолированы — передают user_file явно,
чтобы не зависеть от реального ~/.white-sheet-breaker/templates.json.
"""

import pytest
import json
from pathlib import Path
from breaker.storage.templates import RuleTemplate, TemplateStorage

# Тесты для RuleTemplate


class TestRuleTemplate:
    """Тесты класса RuleTemplate."""

    def test_create_template(self):
        """Создание шаблона с обязательными полями."""
        template = RuleTemplate(
            id="test_template",
            name="Тестовый шаблон",
            signal="сигнал",
            action="действие",
            target="цель",
            action_type="open_file",
        )

        assert template.id == "test_template"
        assert template.name == "Тестовый шаблон"
        assert template.action_type == "open_file"
        assert template.created_at
        assert not template.is_system

    def test_create_template_with_all_fields(self):
        """Создание шаблона со всеми полями."""
        template = RuleTemplate(
            id="full_template",
            name="Полный шаблон",
            signal="сигнал",
            action="действие",
            target="цель",
            action_type="run_shell",
            description="Описание",
            created_at="2026-06-26T10:00:00",
            is_system=True,
        )

        assert template.description == "Описание"
        assert template.created_at == "2026-06-26T10:00:00"
        assert template.is_system is True

    def test_to_dict(self):
        """Преобразование в словарь."""
        template = RuleTemplate(
            id="test",
            name="Test",
            signal="signal",
            action="action",
            target="target",
            action_type="run_shell",
        )

        data = template.to_dict()

        assert data["id"] == "test"
        assert data["action_type"] == "run_shell"
        assert "created_at" in data
        assert "is_system" in data

    def test_to_json(self):
        """Преобразование в JSON-строку."""
        template = RuleTemplate(
            id="test",
            name="Test",
            signal="signal",
            action="action",
            target="target",
            action_type="create_test",
        )

        json_str = template.to_json()

        assert "test" in json_str
        assert "create_test" in json_str
        assert "Test" in json_str

    def test_from_dict(self):
        """Создание из словаря."""
        data = {
            "id": "test",
            "name": "Test",
            "signal": "signal",
            "action": "action",
            "target": "target",
            "action_type": "open_file",
            "created_at": "2026-06-26T10:00:00",
            "is_system": False,
        }

        template = RuleTemplate.from_dict(data)

        assert template.id == "test"
        assert template.action_type == "open_file"
        assert template.created_at == "2026-06-26T10:00:00"

    def test_to_ritual(self):
        """Конвертация шаблона в Ritual."""
        from breaker.core.schema import Ritual, ActionType
        
        template = RuleTemplate(
            id="test_template",
            name="Test",
            signal="файл пуст",
            action="открыть файл",
            target="example.py",
            action_type="open_file",
        )
        
        ritual = template.to_ritual()
        
        assert isinstance(ritual, Ritual)
        assert ritual.signal == "файл пуст"
        assert ritual.action == "открыть файл"
        assert ritual.target == "example.py"
        assert ritual.action_type == ActionType.OPEN_FILE

    def test_to_ritual_invalid_action_type(self):
        """Невалидный action_type — ValueError."""
        template = RuleTemplate(
            id="bad_template",
            name="Bad",
            signal="signal",
            action="action",
            target="target",
            action_type="invalid_type",  # ← невалидный тип
        )
        
        with pytest.raises(ValueError) as exc_info:
            template.to_ritual()
        
        assert "Invalid action_type" in str(exc_info.value)

    def test_full_integration_template_to_executor(self, tmp_path: Path):
        """Полная интеграция: шаблон → Ritual → executor."""
        from breaker.engine.executor import execute_ritual
        
        # Создаём шаблон
        template = RuleTemplate(
            id="create_test_template",
            name="Create Test",
            signal="нет тестов",
            action="создать тест",
            target=str(tmp_path / "test_new.py"),
            action_type="create_test",
        )
        
        # Конвертируем в Ritual
        ritual = template.to_ritual()
        
        # Выполняем через executor
        result = execute_ritual(ritual)
        
        # Проверяем результат
        assert result.success is True
        assert result.evidence_link.startswith("file://")
        assert (tmp_path / "test_new.py").exists()

# Тесты для TemplateStorage


class TestTemplateStorage:
    """Тесты класса TemplateStorage."""

    def test_load_system_templates(self, tmp_path: Path):
        """Загрузка системных шаблонов из файла."""
        system_file = tmp_path / "system_templates.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "sys_1",
                            "name": "System Template",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        }
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        templates = storage.list_templates()

        assert len(templates) == 1
        assert templates[0].id == "sys_1"
        assert templates[0].is_system

    def test_load_empty_system_file(self, tmp_path: Path):
        """Если системного файла нет — хранилище работает."""
        system_file = tmp_path / "nonexistent.json"
        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )

        templates = storage.list_templates()
        assert len(templates) == 0

    def test_save_user_template(self, tmp_path: Path):
        """Сохранение пользовательского шаблона."""
        system_file = tmp_path / "system.json"
        system_file.write_text('{"templates": []}')
        user_file = tmp_path / "user.json"

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )

        template = RuleTemplate(
            id="user_1",
            name="User Template",
            signal="signal",
            action="action",
            target="target",
            action_type="run_shell",
        )

        result = storage.save_template(template)

        assert result is True
        assert user_file.exists()

        loaded = storage.get_template("user_1")
        assert loaded is not None
        assert loaded.name == "User Template"

    def test_delete_user_template(self, tmp_path: Path):
        """Удаление пользовательского шаблона."""
        system_file = tmp_path / "system.json"
        system_file.write_text('{"templates": []}')
        user_file = tmp_path / "user.json"

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )

        template = RuleTemplate(
            id="to_delete",
            name="To Delete",
            signal="signal",
            action="action",
            target="target",
            action_type="create_test",
        )
        storage.save_template(template)

        result = storage.delete_template("to_delete")

        assert result is True
        assert storage.get_template("to_delete") is None

    def test_cannot_delete_system_template(self, tmp_path: Path):
        """Нельзя удалить системный шаблон."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "sys_1",
                            "name": "System",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        }
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        result = storage.delete_template("sys_1")

        assert result is False
        assert storage.get_template("sys_1") is not None

    def test_cannot_overwrite_system_template(self, tmp_path: Path):
        """Нельзя перезаписать системный шаблон."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "sys_1",
                            "name": "System",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        }
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )

        template = RuleTemplate(
            id="sys_1",
            name="Overwrite Attempt",
            signal="new signal",
            action="new action",
            target="new target",
            action_type="run_shell",
        )

        result = storage.save_template(template)

        assert result is False
        loaded = storage.get_template("sys_1")
        assert loaded.name == "System"

    def test_search_templates(self, tmp_path: Path):
        """Поиск шаблонов по названию."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "test_1",
                            "name": "Test Template",
                            "signal": "test signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        },
                        {
                            "id": "prod_1",
                            "name": "Production Template",
                            "signal": "prod signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "run_shell",
                        },
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        results = storage.search_templates("test")

        assert len(results) == 1
        assert results[0].id == "test_1"

    def test_search_by_description(self, tmp_path: Path):
        """Поиск шаблонов по описанию."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "t1",
                            "name": "Template 1",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                            "description": "Это описание с ключевым словом unique_keyword",
                        }
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        results = storage.search_templates("unique_keyword")

        assert len(results) == 1
        assert results[0].id == "t1"

    def test_search_by_signal(self, tmp_path: Path):
        """Поиск шаблонов по сигналу."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "t1",
                            "name": "Template",
                            "signal": "файл пуст",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        }
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        results = storage.search_templates("файл")

        assert len(results) == 1

    def test_list_templates_sorted(self, tmp_path: Path):
        """Список шаблонов отсортирован по названию."""
        system_file = tmp_path / "system.json"
        system_file.write_text(
            json.dumps(
                {
                    "templates": [
                        {
                            "id": "z_template",
                            "name": "Zebra",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "open_file",
                        },
                        {
                            "id": "a_template",
                            "name": "Apple",
                            "signal": "signal",
                            "action": "action",
                            "target": "target",
                            "action_type": "run_shell",
                        },
                    ]
                }
            )
        )

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        templates = storage.list_templates()

        assert templates[0].name == "Apple"
        assert templates[1].name == "Zebra"

    def test_get_template_not_found(self, tmp_path: Path):
        """get_template() возвращает None, если шаблон не найден."""
        system_file = tmp_path / "system.json"
        system_file.write_text('{"templates": []}')

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        result = storage.get_template("nonexistent")

        assert result is None

    def test_delete_nonexistent_template(self, tmp_path: Path):
        """delete_template() возвращает False, если шаблон не найден."""
        system_file = tmp_path / "system.json"
        system_file.write_text('{"templates": []}')

        user_file = tmp_path / "user.json"
        user_file.write_text('{"templates": []}')

        storage = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        result = storage.delete_template("nonexistent")

        assert result is False

    def test_user_templates_persisted(self, tmp_path: Path):
        """Пользовательские шаблоны сохраняются между сессиями."""
        system_file = tmp_path / "system.json"
        system_file.write_text('{"templates": []}')
        user_file = tmp_path / "user.json"

        storage1 = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        template = RuleTemplate(
            id="persistent",
            name="Persistent",
            signal="signal",
            action="action",
            target="target",
            action_type="open_file",
        )
        storage1.save_template(template)

        storage2 = TemplateStorage(
            system_file=str(system_file),
            user_file=str(user_file),
        )
        loaded = storage2.get_template("persistent")

        assert loaded is not None
        assert loaded.name == "Persistent"
