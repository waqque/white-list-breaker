"""Хранилище шаблонов правил "если-то".

Этот модуль отвечает за:
- Загрузку шаблонов из JSON-файла
- Сохранение новых пользовательских шаблонов
- Удаление пользовательских шаблонов
- Получение списка всех шаблонов
- Поиск шаблонов по названию/описанию

"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RuleTemplate:
    """Шаблон правила "если-то".
    
    Это заготовка правила, которую студент может выбрать и адаптировать
    под свою текущую задачу. Шаблон содержит все поля Ritual, кроме
    task_id (который устанавливается при запуске).
    
    """
    id: str
    name: str
    signal: str
    action: str
    target: str
    action_type: str  # "open_file", "run_shell", "create_test"
    description: str = ""
    created_at: str = ""
    is_system: bool = False
    
    def __post_init__(self):
        """Установить время создания, если не задано."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь (для JSON)."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Преобразовать в JSON-строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RuleTemplate":
        """Создать из словаря."""
        return cls(**data)

    def to_ritual(self):
        """Конвертировать шаблон в объект Ritual для executor.py."""
        
        from breaker.core.schema import Ritual, ActionType
        
        try:
            action_type = ActionType(self.action_type)
        except ValueError as e:
            raise ValueError(
                f"Invalid action_type in template '{self.id}': {self.action_type}. "
                f"Valid types: {[t.value for t in ActionType]}"
            ) from e
        
        return Ritual(
            signal=self.signal,
            action=self.action,
            target=self.target,
            action_type=action_type,
        )
        
class TemplateStorage:
    """Хранилище шаблонов правил.
    """
    
    def __init__(
        self,
        system_file: str = "data/examples/default_templates.json",
        user_file: Optional[str] = None,
    ):
        """Инициализировать хранилище.
        """
        self.system_file = Path(system_file)
        
        if user_file is None:
            # Пользовательские шаблоны в домашней директории
            user_dir = Path.home() / ".white-sheet-breaker"
            user_dir.mkdir(parents=True, exist_ok=True)
            self.user_file = user_dir / "templates.json"
        else:
            self.user_file = Path(user_file)
        
        # Загружаем шаблоны при инициализации
        self._system_templates: dict[str, RuleTemplate] = {}
        self._user_templates: dict[str, RuleTemplate] = {}
        self._load_system_templates()
        self._load_user_templates()
    
    def _load_system_templates(self) -> None:
        """Загрузить системные шаблоны из файла."""
        if not self.system_file.exists():
            return
        
        try:
            with open(self.system_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for item in data.get("templates", []):
                template = RuleTemplate.from_dict(item)
                template.is_system = True  # Системные шаблоны нельзя удалять
                self._system_templates[template.id] = template
        except Exception as e:
            print(f"  Ошибка загрузки системных шаблонов: {e}")
    
    def _load_user_templates(self) -> None:
        """Загрузить пользовательские шаблоны из файла."""
        if not self.user_file.exists():
            return
        
        try:
            with open(self.user_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for item in data.get("templates", []):
                template = RuleTemplate.from_dict(item)
                self._user_templates[template.id] = template
        except Exception as e:
            print(f"  Ошибка загрузки пользовательских шаблонов: {e}")
    
    def _save_user_templates(self) -> None:
        """Сохранить пользовательские шаблоны в файл."""
        self.user_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "templates": [t.to_dict() for t in self._user_templates.values()]
        }
        
        with open(self.user_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def list_templates(self, include_system: bool = True) -> list[RuleTemplate]:
        """Получить список всех шаблонов.
        """
        templates = []
        
        if include_system:
            templates.extend(self._system_templates.values())
        
        templates.extend(self._user_templates.values())
        
        return sorted(templates, key=lambda t: t.name)
    
    def get_template(self, template_id: str) -> Optional[RuleTemplate]:
        """Получить шаблон по ID.
        """
        if template_id in self._user_templates:
            return self._user_templates[template_id]
        
        if template_id in self._system_templates:
            return self._system_templates[template_id]
        
        return None
    
    def save_template(self, template: RuleTemplate) -> bool:
        """Сохранить новый шаблон (пользовательский).
        """
        if template.id in self._system_templates:
            print(f" Нельзя перезаписать системный шаблон: {template.id}")
            return False
        
        self._user_templates[template.id] = template
        self._save_user_templates()
        
        print(f" Шаблон сохранён: {template.name}")
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """Удалить шаблон (только пользовательский).
        """
        if template_id in self._system_templates:
            print(f" Нельзя удалить системный шаблон: {template_id}")
            return False
        
        if template_id in self._user_templates:
            del self._user_templates[template_id]
            self._save_user_templates()
            print(f" Шаблон удалён: {template_id}")
            return True
        
        print(f"  Шаблон не найден: {template_id}")
        return False
    
    def search_templates(self, query: str) -> list[RuleTemplate]:
        """Поиск шаблонов по названию, описанию или сигналу.
        """
        query_lower = query.lower()
        results = []
        
        for template in self.list_templates():
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                query_lower in template.signal.lower()):
                results.append(template)
        
        return results