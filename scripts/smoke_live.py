"""Run a minimal live API smoke request."""

import asyncio

from app.config import get_settings
from app.container import Container
from app.infra.db.session import build_engine, build_session_factory
from app.services.task_service import TaskService


async def main() -> None:
    """Create one task through TaskService and print the result."""
    settings = get_settings()
    container = Container(settings)
    session_factory = build_session_factory(build_engine(settings.db_url))
    service = TaskService(container, session_factory, run_background=False)
    task_id = await service.create_task("AI 编程助手赛道", [], [])
    print(service.get_status(task_id))


if __name__ == "__main__":
    asyncio.run(main())
