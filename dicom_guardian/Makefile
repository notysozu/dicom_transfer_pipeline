PYTHON ?= python3.11
VENV_DIR ?= .venv
PIP := $(VENV_DIR)/bin/pip
PYTEST := $(VENV_DIR)/bin/pytest
RUFF := $(VENV_DIR)/bin/ruff
MYPY := $(VENV_DIR)/bin/mypy
UVICORN := $(VENV_DIR)/bin/uvicorn

.PHONY: venv install install-dev freeze run run-secure init-db db-health db-test security-test test lint typecheck clean

venv:
	$(PYTHON) -m venv $(VENV_DIR)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

freeze:
	$(PIP) freeze

run:
	$(VENV_DIR)/bin/python -m app.main

run-secure:
	$(VENV_DIR)/bin/python -m app.main

init-db:
	$(VENV_DIR)/bin/python -m app.database.db

db-health:
	$(VENV_DIR)/bin/python -c "from app.database.db import check_database_health; print(check_database_health())"

db-test:
	$(VENV_DIR)/bin/python -m app.database.connection_test

security-test:
	$(VENV_DIR)/bin/python -m app.security.security_test

test:
	$(PYTEST)

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) app

clean:
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
