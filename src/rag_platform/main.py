"""ASGI entrypoint for uvicorn and Docker."""

from rag_platform.api.app import app

__all__ = ["app"]
