"""Security review F7, spec FR-030/SC-014: 5 requests per 15 minutes per source IP on
/auth/register."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from src.main import app
from tests.helpers import DEFAULT_PASSWORD


async def test_sixth_registration_attempt_from_one_source_ip_is_rate_limited(
    client: AsyncClient,
):
    for i in range(5):
        resp = await client.post(
            "/auth/register",
            json={"email": f"user{i}@example.com", "password": DEFAULT_PASSWORD},
        )
        assert resp.status_code == 201, f"attempt {i} unexpectedly failed: {resp.text}"

    sixth = await client.post(
        "/auth/register", json={"email": "user6@example.com", "password": DEFAULT_PASSWORD}
    )
    assert sixth.status_code == 429


async def test_a_different_source_ip_is_unaffected_by_another_ips_limit(client: AsyncClient):
    for i in range(5):
        await client.post(
            "/auth/register",
            json={"email": f"sameip{i}@example.com", "password": DEFAULT_PASSWORD},
        )

    # A separate client "from" a different source IP shares the same `app` (and therefore the
    # same `get_db` override the `client` fixture already installed), so it hits the same
    # test database - but rate limiting keys on source IP, so it must be unaffected.
    other_ip_transport = ASGITransport(app=app, client=("10.0.0.99", 12345))
    async with AsyncClient(
        transport=other_ip_transport, base_url="http://test"
    ) as other_ip_client:
        resp = await other_ip_client.post(
            "/auth/register",
            json={"email": "fromdifferentip@example.com", "password": DEFAULT_PASSWORD},
        )
    assert resp.status_code == 201
