"""Feature 002 BE-016/US10 AC1/AC4: behind a configured trusted reverse proxy, the existing
per-source-IP rate limiter keys on the real forwarded client address, not the shared proxy
address - so two different real clients going through the same proxy are limited independently."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.config import settings
from src.infrastructure.db.session import get_db
from src.main import app

PROXY_IP = "10.0.0.1"


@pytest.fixture(autouse=True)
def _trust_the_proxy():
    original = settings.trusted_proxy_ips
    settings.trusted_proxy_ips = [PROXY_IP]
    yield
    settings.trusted_proxy_ips = original


@pytest.fixture
async def proxied_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app, client=(PROXY_IP, 0))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_two_forwarded_clients_through_the_same_proxy_are_limited_independently(
    proxied_client: AsyncClient,
):
    for i in range(5):
        resp = await proxied_client.post(
            "/auth/password-reset/request",
            json={"email": f"clientA{i}@example.com"},
            headers={"X-Forwarded-For": "203.0.113.5"},
        )
        assert resp.status_code == 202, f"client A attempt {i} unexpectedly failed: {resp.text}"

    sixth_a = await proxied_client.post(
        "/auth/password-reset/request",
        json={"email": "clientA6@example.com"},
        headers={"X-Forwarded-For": "203.0.113.5"},
    )
    assert sixth_a.status_code == 429

    first_b = await proxied_client.post(
        "/auth/password-reset/request",
        json={"email": "clientB1@example.com"},
        headers={"X-Forwarded-For": "198.51.100.9"},
    )
    assert first_b.status_code == 202
