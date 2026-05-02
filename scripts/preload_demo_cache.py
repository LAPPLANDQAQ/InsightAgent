"""Preload demo tasks into the local cache and database."""

import asyncio

from app.config import get_settings
from app.container import Container
from app.infra.db.session import build_engine, build_session_factory
from app.services.task_service import TaskService

DEMO_QUERIES = [
    "AI 编程助手赛道",
    "向量数据库产品对比",
    "AI Agent 框架对比",
]


async def main() -> None:
    """Run demo tasks sequentially."""
    settings = get_settings()
    container = Container(settings)
    session_factory = build_session_factory(build_engine(settings.db_url))
    service = TaskService(container, session_factory, run_background=False)
    for query in DEMO_QUERIES:
        task_id = await service.create_task(query, [], [])
        status = service.get_status(task_id)
        print(f"{task_id} {query} {status['status']}")


if __name__ == "__main__":
    asyncio.run(main())
