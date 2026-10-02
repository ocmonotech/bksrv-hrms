from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 — register ORM metadata
from app.core.config import get_settings
from app.core.database import create_database_engine, get_db
from app.factory import create_app
from app.models.base import Base
from app.services.auth_service import create_super_admin
from app.services.rbac_seed_service import RBACSeedService


@pytest.fixture
def test_app():
    settings = get_settings()
    engine = create_database_engine(settings.test_database_url, echo=False)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed_db = session_factory()
    RBACSeedService(seed_db).seed_all()
    create_super_admin(seed_db)
    seed_db.commit()
    seed_db.close()

    def override_get_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    def _test_db_check() -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    app.state.check_database_connection = _test_db_check

    with TestClient(app) as test_client:
        yield test_client, session_factory

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(test_app) -> TestClient:
    test_client, _ = test_app
    return test_client


@pytest.fixture
def db_session_factory(test_app):
    _, session_factory = test_app
    return session_factory
