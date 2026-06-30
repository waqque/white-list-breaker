PYTHON       ?= python3
MODULE       := breaker
SRC_DIR      := src/$(MODULE)
TESTS_DIR    := tests
CONFIGS_DIR  := configs
PROMPTS_DIR  := prompts
DATA_DIR     := data
EXAMPLES_DIR := $(DATA_DIR)/examples
DOCS_DIR     := docs
SCRIPTS_DIR  := scripts
LOGS_DIR     := logs

# Режим работы LRS: mock (stdout) или real (отправка в LRS)
LRS_MODE     ?= mock


.DEFAULT_GOAL := help
.PHONY: help \
        init init-dirs init-files \
        install install-dev \
        test test-core test-engine test-ui test-cov \
        demo run-cli run-api \
        docker-build docker-up docker-down \
        clean logs



init: init-dirs init-files 


init-dirs: ## Создать директории 
	@mkdir -p $(SRC_DIR)/core
	@mkdir -p $(SRC_DIR)/engine
	@mkdir -p $(SRC_DIR)/ui
	@mkdir -p $(SRC_DIR)/storage
	@mkdir -p $(TESTS_DIR)
	@mkdir -p $(CONFIGS_DIR)
	@mkdir -p $(PROMPTS_DIR)
	@mkdir -p $(EXAMPLES_DIR)
	@mkdir -p $(DOCS_DIR)
	@mkdir -p $(SCRIPTS_DIR)
	@mkdir -p $(LOGS_DIR)

init-files: ## Создать файлы-заглушки
	# Точка входа Python-модуля
	@test -f $(SRC_DIR)/__init__.py          || echo '"""White-sheet-breaker module."""' > $(SRC_DIR)/__init__.py
	@test -f $(SRC_DIR)/__main__.py          || echo '# Entry point: python -m breaker' > $(SRC_DIR)/__main__.py
	@test -f $(SRC_DIR)/main.py              || echo '# Orchestrator' > $(SRC_DIR)/main.py

	# Подпакеты
	@test -f $(SRC_DIR)/core/__init__.py     || touch $(SRC_DIR)/core/__init__.py
	@test -f $(SRC_DIR)/engine/__init__.py   || touch $(SRC_DIR)/engine/__init__.py
	@test -f $(SRC_DIR)/ui/__init__.py       || touch $(SRC_DIR)/ui/__init__.py
	@test -f $(SRC_DIR)/storage/__init__.py  || touch $(SRC_DIR)/storage/__init__.py

	# Корневые файлы проекта 
	@test -f README.md        || echo "# White-sheet-breaker\n\nМодуль ритуала начала задачи." > README.md
	@test -f module.yaml      || echo "\nname: white-sheet-breaker\ntitle: White-sheet-breaker\ntype: learner-side\nstatus: draft" > module.yaml
	@test -f pyproject.toml   || echo "[project]\nname = \"white-sheet-breaker\"\nversion = \"0.1.0\"" > pyproject.toml
	@test -f requirements.txt || touch requirements.txt
	@test -f .env.example     || echo "# LRS \nLRS_URL=http://localhost:8080/xAPI\nLRS_KEY=\nLRS_SECRET=\nLRS_MODE=mock" > .env.example
	@test -f .gitignore       || echo "__pycache__/\n*.pyc\n.env\nlogs/*.log\n.pytest_cache/\nhtmlcov/" > .gitignore

	# .gitkeep в опциональных директориях
	@touch $(CONFIGS_DIR)/.gitkeep
	@touch $(PROMPTS_DIR)/.gitkeep
	@touch $(EXAMPLES_DIR)/.gitkeep
	@touch $(DOCS_DIR)/.gitkeep
	@touch $(SCRIPTS_DIR)/.gitkeep
	@touch $(LOGS_DIR)/.gitkeep
	@touch $(TESTS_DIR)/.gitkeep


install: ## Установить зависимости (pip install -r requirements.txt)
	@test -f requirements.txt || (echo "Файл requirements.txt не найден. Создайте его или запустите 'make init'." && exit 1)
	pip install -r requirements.txt
	pip install -e .

install-dev: ## Установить зависимости + инструменты разработки (pytest, flake8, black)
	@test -f requirements.txt || (echo "Файл requirements.txt не найден." && exit 1)
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 black

test: ## Запустить все тесты
	$(PYTHON) -m pytest $(TESTS_DIR) -v

test-core: ## Запустить тесты ядра (schema, tracker, xapi)
	$(PYTHON) -m pytest $(TESTS_DIR)/test_schema.py \
	                   $(TESTS_DIR)/test_tracker.py \
	                   $(TESTS_DIR)/test_xapi.py -v

test-engine: ## Запустить тесты движка (executor, templates)
	$(PYTHON) -m pytest $(TESTS_DIR)/test_executor.py \
	                   $(TESTS_DIR)/test_templates.py -v

test-ui: ## Запустить тесты UI (dialog, timer)
	$(PYTHON) -m pytest $(TESTS_DIR)/test_dialog.py \
	                   $(TESTS_DIR)/test_timer.py \
	                   $(TESTS_DIR)/test_help_menu.py \
	                   $(TESTS_DIR)/test_activity_monitor.py \
	                   $(TESTS_DIR)/test_template_editor.py -v

demo: ## Демонстрация работы модуля (пример задачи + правило + шаг)
	LRS_MODE=mock $(PYTHON) -m $(MODULE) --demo

run-cli: ## Запустить CLI-интерфейс модуля
	LRS_MODE=$(LRS_MODE) $(PYTHON) -m $(MODULE)


docker-build: ## Собрать Docker-контейнер (с заглушками)
	docker build -t white-sheet-breaker:latest .

docker-up: ## Поднять контейнер/сервис
	docker-compose up -d

docker-down: ## Остановить контейнер
	docker-compose down
 lint: ## Проверить код через flake8
	$(PYTHON) -m flake8 src/ tests/ --max-line-length=100

format: ## Отформатировать код через black
	$(PYTHON) -m black src/ tests/ --line-length=100

clean: ## Очистить артефакты: __pycache__, .pytest_cache, htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage

logs: ## Показать последние 50 строк лога (logs/breaker.log)
	@test -f $(LOGS_DIR)/breaker.log || (echo "Лог ещё не создан." && exit 0)
	tail -n 50 $(LOGS_DIR)/breaker.log

help: ## Показать список команд
	@echo "============================================================"
	@echo "  White-sheet-breaker — доступные команды"
	@echo "============================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'