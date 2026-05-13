"""Database engine and session helpers."""

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.infra.db.models import Base


def build_engine(db_url: str) -> Engine:
    """Build a SQLAlchemy engine and initialize tables.

    Args:
        db_url: SQLAlchemy database URL.

    Returns:
        Configured engine.
    """
    _ensure_sqlite_parent_dir(db_url)
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


def _ensure_sqlite_parent_dir(db_url: str) -> None:
    """Create the parent directory for file-backed SQLite databases."""
    url = make_url(db_url)
    if url.drivername.split("+", 1)[0] != "sqlite":
        return
    database = url.database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


def build_session_factory(engine: Engine) -> Callable[[], Session]:
    """Build a session factory.

    Args:
        engine: SQLAlchemy engine.

    Returns:
        Callable returning a new Session.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
