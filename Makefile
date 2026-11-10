.PHONY: help install test lint eval eval-matrix demo compose-up compose-config migrate

help:
	@echo "install test lint eval eval-matrix demo compose-up compose-config migrate"

install:
	uv sync --extra dev

test:
	uv run pytest -q

demo:
	uv run python scripts/demo.py

eval:
	uv run python scripts/eval.py

eval-matrix:
	uv run python scripts/eval_matrix.py

lint:
	uv run ruff check .

compose-up:
	docker compose up -d postgres redis minio

compose-config:
	docker compose config

migrate:
	uv run alembic upgrade head
