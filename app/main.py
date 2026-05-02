"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.tasks import router as tasks_router
from app.config import get_settings
from app.container import Container
from app.infra.db.session import build_engine, build_session_factory
from app.infra.logger import setup_logger
from app.services.task_service import TaskService


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
    app.state.task_service = TaskService(container, session_factory)
    app.include_router(tasks_router)
    return app


app = create_app()
