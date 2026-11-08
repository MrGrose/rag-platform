.PHONY: help install test lint compose-up compose-config migrate

help:
	@echo "install test lint compose-up compose-config migrate"

install:
	uv sync --extra dev

test:
	uv run pytest -q

lint:
	uv run ruff check .

compose-up:
	docker compose up -d postgres redis minio

compose-config:
	docker compose config

migrate:
	uv run alembic upgrade head
