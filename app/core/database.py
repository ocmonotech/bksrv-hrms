from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()


def create_database_engine(url: Optional[str] = None, *, echo: Optional[bool] = None) -> Engine:
    db_url = url or settings.database_url
    echo_sql = settings.database_echo if echo is None else echo

    engine_kwargs = {
        "echo": echo_sql,
        "pool_pre_ping": True,
    }

    if db_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if db_url in ("sqlite://", "sqlite:///:memory:"):
            engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_recycle": settings.database_pool_recycle,
                "pool_timeout": settings.database_pool_timeout,
            }
        )

    return create_engine(db_url, **engine_kwargs)


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
