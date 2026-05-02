"""Small database repository helpers."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.infra.db.models import Task


class TaskRepository:
    """Repository for task rows."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def create(self, *, task_id: str, query: str) -> None:
        """Create a task row.

        Args:
            task_id: Task identifier.
            query: User query.
        """
        with self.session_factory() as session:
            session.add(Task(id=task_id, query=query, status="PENDING"))
            session.commit()

    def set_status(self, *, task_id: str, status: str, stage: str | None = None) -> None:
        """Update task status.

        Args:
            task_id: Task identifier.
            status: New task status.
            stage: Current workflow stage.
        """
        with self.session_factory() as session:
            task = session.get(Task, task_id)
            if task:
                task.status = status
                task.current_stage = stage
                task.updated_at = datetime.utcnow()
                session.commit()
