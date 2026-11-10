#!/usr/bin/env bash
# Bring up local infrastructure, migrate, ingest three documents and ask questions.
set -euo pipefail

uv run alembic upgrade head
uv run python scripts/demo.py
