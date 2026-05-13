"""Health check service."""

from typing import Any

from sqlalchemy import Engine, text

from app.config import Settings
from app.infra.cache.base import CacheBackend


async def build_health_payload(
    *,
    settings: Settings,
    engine: Engine,
    cache: CacheBackend,
) -> tuple[dict[str, Any], bool]:
    """Build a runtime health payload and readiness flag."""
    checks: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {type(exc).__name__}"

    try:
        cache_key = "__healthz__"
        await cache.set(cache_key, b"ok", ttl=30)
        checks["cache"] = "ok" if await cache.get(cache_key) == b"ok" else "error: unreadable"
        await cache.delete(cache_key)
    except Exception as exc:
        checks["cache"] = f"error: {type(exc).__name__}"

    llm_configured = is_configured_key(settings.llm_api_key)
    config_ok = (
        settings.llm_provider == "deepseek"
        and settings.llm_base_url.strip().startswith(("https://", "http://"))
        and bool(settings.llm_heavy_model.strip())
        and bool(settings.llm_light_model.strip())
        and bool(settings.llm_fallback_model.strip())
    )
    checks["config"] = "ok" if config_ok else "error: invalid runtime configuration"
    checks["llm"] = "ok" if llm_configured else "degraded: missing DeepSeek API key"

    ok = (
        checks["db"] == "ok"
        and checks["cache"] == "ok"
        and checks["config"] == "ok"
        and llm_configured
    )
    payload = {
        "status": "ok" if ok else "degraded",
        "app": "InsightAgent",
        "db": checks["db"],
        "cache": checks["cache"],
        "config": checks["config"],
        "llm_provider": settings.llm_provider,
        "llm_configured": llm_configured,
    }
    return payload, ok


def is_configured_key(value: str) -> bool:
    """Return whether a configured key is present and not a placeholder."""
    key = value.strip()
    return bool(key and key.lower() not in {"your_deepseek_key_here", "changeme", "change-me"})
