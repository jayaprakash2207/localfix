"""Shared test helpers: not test files themselves, just utilities imported by them."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import UserAccount
from src.infrastructure.security.hashing import hash_password

DEFAULT_PASSWORD = "Str0ngP@ssw0rd!"


async def register_and_login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    login_resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["session_token"]


def seed_user(
    db: DBSession,
    *,
    email: str,
    password: str = DEFAULT_PASSWORD,
    role: Role = Role.CITIZEN,
    status: AccountStatus = AccountStatus.ACTIVE,
) -> UserAccount:
    """Directly insert a user, bypassing the API — used to seed the first Admin (chicken-and-egg,
    same as scripts/seed_admin.py) or to set up fixtures that the API itself cannot create."""
    user = UserAccount(email=email, password_hash=hash_password(password), role=role, status=status)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["session_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
