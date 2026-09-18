"""SQLite engine/session setup.

WAL journal mode + busy_timeout, per data_integration decision DAT-3
(DATA-AND-INTEGRATION-conversational-crm-T-1-v2.0.md).
"""
import os
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

Base = declarative_base()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def make_engine(database_path: str | None = None):
    settings = get_settings()
    path = database_path or settings.database_path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # DAT-3: WAL mode allows concurrent readers alongside a single writer.
        cursor.execute("PRAGMA journal_mode=WAL")
        # DAT-3: 5000ms busy_timeout before SQLITE_BUSY is raised to the app.
        cursor.execute("PRAGMA busy_timeout=5000")
        # Referential and lifecycle notes (DATA-MODEL Section 1.5): interaction_id
        # FKs enforced at the application layer via this pragma.
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


_engine = None
_SessionLocal = None


def init_engine(database_path: str | None = None):
    global _engine, _SessionLocal
    _engine = make_engine(database_path)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(_engine)
    return _engine


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


def get_session_factory():
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal


def get_db():
    """FastAPI dependency: yields a session, closes it after the request."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
