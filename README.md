# White-sheet-breaker


[![PyPI version](https://img.shields.io/pypi/v/white-sheet-breaker.svg)](https://pypi.org/project/white-sheet-breaker/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/white-sheet-breaker.svg)](https://pypi.org/project/white-sheet-breaker/)
[![License: MIT](https://img.shields.io/pypi/l/white-sheet-breaker.svg)](https://github.com/waqque/white-list-breaker/blob/main/LICENSE)


CLI-инструмент для преодоления прокрастинации через правила «если-то».

> Превращение размытого намерения в конкретное правило «ЕСЛИ [сигнал] → ТО [действие]» и немедленное выполнение микро-шага снижает психологическое сопротивление.

---

## О проекте

White-sheet-breaker помогает преодолеть барьер начала работы. Вместо того чтобы писать код за пользователя (как Copilot), модуль помогает **сделать первый шаг**: сформулировать правило, создать файл с шаблоном и мягко подтолкнуть к действию, если пользователь завис.

### Возможности

- Формулировка правил «если-то» через интерактивный диалог
- Библиотека готовых шаблонов правил с редактором
- Создание и открытие файлов с автоопределением шаблона по расширению
- Встроенный Pomodoro-таймер с кроссплатформенным звуком
- Фоновое наблюдение за активностью пользователя
- Адаптивные меню помощи при бездействии (2 уровня)
- Параллельная работа таймера и наблюдения
- Логирование в NDJSON и отправка xAPI-стейтментов в LRS
- Статистика выполненных ритуалов

---

## Быстрый старт

### Требования

- Python 3.10+
- pip

### Установка

**Из PyPI (рекомендуется):**

```bash
pip install white-sheet-breaker
```

**Из исходного кода:**
```bash
# Клонировать репозиторий
git clone https://github.com/waqque/white-list-breaker.git
cd white-list-breaker

# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Установить зависимости
pip install -e .
```

### Запуск

```bash
# Интерактивный режим
python -m breaker

# Демо-режим (без ввода)
python -m breaker --demo

# Без Pomodoro-таймера
python -m breaker --no-timer
```

---

## Сценарии работы

### Сценарий 1: С Pomodoro-таймером

1. Пользователь создаёт правило: «ЕСЛИ файл пуст → ТО напишу класс → classes.py»
2. Создаётся файл `classes.py` с python-шаблоном
3. Параллельно запускаются:
   - Pomodoro-таймер (обратный отсчёт)
   - Фоновое наблюдение (отслеживание файла)
4. При бездействии 1 минута — меню уровня 1, через 3 минуты — уровень 2
5. При активности >100 символов — «Работа началась» и модуль останавливается
6. После завершения таймера — наблюдение не останавливается
7. Логирование в NDJSON + отправка xAPI-стейтмента

### Сценарий 2: Без таймера

1. Пользователь создаёт правило
2. Создаётся файл
3. Запускается только фоновое наблюдение
4. Наблюдение работает до:
   - Активности пользователя (>100 символов) → успех
   - Таймаута (5 минут) → завершение
5. Логирование + xAPI

---

## Пример использования

```
$ python -m breaker

[1] Создать правило с нуля

Сигнал: файл пуст
Действие: напишу класс
Режим: Создать файл
Файл: classes.py

ЕСЛИ:  файл пуст
ТО:    напишу класс
ЦЕЛЬ:  classes.py

Подтверждаете? [y/n]: y

Файл создан: classes.py
Запускаю фоновое наблюдение...

Запустить Pomodoro-таймер? [y/n]: y
Сколько минут? (5): 25

Осталось: 00:32 ━━━━╸━━━  47%   ← таймер идёт
[1] Шаблон функции              ← меню помощи появилось
[2] Шаблон класса               ← пользователь выбрал
...
Осталось: 00:26 ━━━━━╸━━  57%   ← таймер продолжает идти!
Шаблон 'class' добавлен в конец файла

Осталось: 00:16 ━━━━━━╺━━  73%
Отлично! Работа началась.
```

---

## Тестирование

```bash
# Все тесты
make test

# С покрытием
python -m pytest tests/ --cov=breaker --cov-report=term-missing -v

# Отдельные группы
make test-core      # schema, tracker, xapi
make test-engine    # executor, templates
make test-ui        # dialog, timer, help_menu, activity_monitor
```

### Статистика

| Метрика | Значение |
|---|---|
| Всего тестов | 315 |
| Покрытие кода | ~88% |
| Платформы | Windows, macOS, Linux, WSL |

---

## Команды Makefile

| Команда | Назначение |
|---|---|
| `make install` | Установка зависимостей |
| `make install-dev` | Установка + dev-инструменты |
| `make test` | Запуск всех тестов |
| `make run-cli` | Запуск CLI в mock-режиме |
| `make demo` | Демо-режим без ввода |
| `make lint` | Проверка стиля (flake8) |
| `make format` | Форматирование (black) |
| `make logs` | Последние 50 строк лога |
| `make clean` | Очистка артефактов |

---

## Конфигурация

Переменные окружения (в `.env` или экспортом):

```bash
# LRS (Learning Record Store)
LRS_URL=http://localhost:8080/xAPI
LRS_KEY=your_key
LRS_SECRET=your_secret
LRS_MODE=mock              # или "real"

# Идентификация учащегося
LEARNER_ID=student123
LEARNER_NAME=Иван Иванов
COURSE_ID=course-python-101
```

---

## Структура проекта

```
white-list-breaker/
├── src/breaker/
│   ├── core/          # Модели данных, логирование, xAPI
│   ├── engine/        # Исполнение действий, шаблоны
│   ├── storage/       # Хранилище шаблонов правил
│   ├── ui/            # Интерфейс, таймер, наблюдение
│   └── main.py        # Оркестратор
├── tests/             # 315 теста
├── docs/              # Документация
├── logs/              # NDJSON-логи
└── Makefile
```

---

## Команда

| Участник | Зона | Модули |
|---|---|---|
| А | Core | `schema.py`, `tracker.py`, `xapi_client.py` |
| Б | Engine + Storage | `executor.py`, `file_templates.py`, `templates.py` |
| В | UI | `dialog.py`, `timer.py`, `activity_monitor.py`, `help_menu.py`, `template_editor.py` |

---

## Документация

- **PyPI:** https://pypi.org/project/white-sheet-breaker/
- **Репозиторий:** https://github.com/waqque/white-list-breaker

Подробная документация находится в директории [`docs/`](./docs/):

- [DOMAIN.md](./docs/DOMAIN.md) — предметная область и психологическая основа
- [SPECIFICATION.md](./docs/SPECIFICATION.md) — функциональные и нефункциональные требования
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — архитектура системы и структура проекта
- [IMPLEMENTATION.md](./docs/IMPLEMENTATION.md) — описание реализованной системы

---

## Зависимости

### Runtime

```
rich>=13.0.0
requests>=2.31.0
```

### Development

```
pytest>=7.4.0
pytest-cov>=4.1.0
flake8>=6.1.0
black>=23.7.0
```

---
