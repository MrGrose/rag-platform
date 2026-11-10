.PHONY: help install test lint eval compose-up compose-config migrate

help:
	@echo "install test lint eval compose-up compose-config migrate"

install:
	uv sync --extra dev

test:
	uv run pytest -q

eval:
	uv run python scripts/eval.py

lint:
	uv run ruff check .

compose-up:
	docker compose up -d postgres redis minio

compose-config:
	docker compose config

migrate:
	uv run alembic upgrade head
