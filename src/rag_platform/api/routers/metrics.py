from fastapi import APIRouter, Response

from rag_platform.infrastructure.metrics import metrics_body

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    body, content_type = metrics_body()
    return Response(content=body, media_type=content_type)
