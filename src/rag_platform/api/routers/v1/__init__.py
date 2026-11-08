from fastapi import APIRouter

from rag_platform.api.constants import API_PREFIX
from rag_platform.api.routers.v1 import chat, documents, evaluations, queries

router = APIRouter(prefix=API_PREFIX)
router.include_router(documents.router)
router.include_router(chat.router)
router.include_router(queries.router)
router.include_router(evaluations.router)
