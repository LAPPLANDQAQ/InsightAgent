"""Runtime health and readiness routes."""

from typing import Any

from fastapi import APIRouter, Request, Response

from app.services.health_service import build_health_payload

router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request, response: Response) -> dict[str, Any]:
    """Return dependency health without exposing secrets."""
    payload, ok = await build_health_payload(
        settings=request.app.state.settings,
        engine=request.app.state.engine,
        cache=request.app.state.container.cache,
    )
    if not ok:
        response.status_code = 503
    return payload
