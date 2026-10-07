"""Security review F7, spec FR-030/SC-014: 5 requests per 15 minutes per source IP on
/auth/password-reset/request."""

from __future__ import annotations

from httpx import AsyncClient


async def test_sixth_reset_request_from_one_source_ip_is_rate_limited(client: AsyncClient):
    for i in range(5):
        resp = await client.post(
            "/auth/password-reset/request", json={"email": f"nobody{i}@example.com"}
        )
        assert resp.status_code == 202, f"attempt {i} unexpectedly failed: {resp.text}"

    sixth = await client.post(
        "/auth/password-reset/request", json={"email": "nobody6@example.com"}
    )
    assert sixth.status_code == 429
