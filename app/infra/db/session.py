"""Database engine and session helpers."""

from collections.abc import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infra.db.models import Base


def build_engine(db_url: str) -> Engine:
    """Build a SQLAlchemy engine and initialize tables.

    Args:
        db_url: SQLAlchemy database URL.

    Returns:
        Configured engine.
    """
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(engine: Engine) -> Callable[[], Session]:
    """Build a session factory.

    Args:
        engine: SQLAlchemy engine.

    Returns:
        Callable returning a new Session.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
