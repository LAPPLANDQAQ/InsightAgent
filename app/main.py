"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.tasks import router as tasks_router
from app.config import get_settings
from app.container import Container
from app.infra.db.session import build_engine, build_session_factory
from app.infra.logger import get_logger, setup_logger
from app.services.task_service import TaskService

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Returns:
        Configured FastAPI app.
    """
    settings = get_settings()
    setup_logger(settings.log_level)
    container = Container(settings)
    engine = build_engine(settings.db_url)
    session_factory = build_session_factory(engine)
    app = FastAPI(title="InsightAgent")
    app.state.settings = settings
    app.state.container = container
    app.state.engine = engine
    app.state.task_service = TaskService(container, session_factory)
    logger.info(
        "startup_config",
        extra={
            "app_env": settings.app_env,
            "cache_backend": settings.cache_backend,
            "db_url": _safe_db_url(settings.db_url),
            "llm_provider": settings.llm_provider,
            "llm_base_url": settings.llm_base_url,
            "llm_heavy_model": settings.llm_heavy_model,
            "llm_light_model": settings.llm_light_model,
            "llm_fallback_model": settings.llm_fallback_model,
            "llm_configured": bool(settings.llm_api_key.strip()),
        },
    )
    app.include_router(health_router)
    app.include_router(tasks_router)
    return app


def _safe_db_url(db_url: str) -> str:
    """Return a DB URL summary without credentials."""
    if "@" not in db_url:
        return db_url
    scheme, _, rest = db_url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}"


app = create_app()
