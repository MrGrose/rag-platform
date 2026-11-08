from fastapi import APIRouter, HTTPException

from rag_platform.infrastructure.health import check_postgres, check_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    try:
        await check_postgres()
        await check_redis()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"not ready: {exc}") from exc
    return {"status": "ready"}
