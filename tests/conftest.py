from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from src.domain.models import Role
from src.infrastructure.config import settings
from src.infrastructure.db.session import get_db
from src.main import app

TEST_DB_URL = settings.test_database_url or settings.database_url
engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_TABLES = (
    "sessions, password_reset_requests, login_attempt_records, rate_limit_records, "
    "audit_records, user_accounts"
)


@pytest.fixture(autouse=True)
def _clean_db():
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_TABLES} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db() -> DBSession:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def client(db: DBSession):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_token(db: DBSession, client: AsyncClient) -> str:
    from tests.helpers import DEFAULT_PASSWORD, login, seed_user

    seed_user(db, email="seed-admin@example.com", role=Role.ADMIN)
    return await login(client, "seed-admin@example.com", DEFAULT_PASSWORD)
