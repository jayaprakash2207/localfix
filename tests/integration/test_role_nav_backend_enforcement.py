"""Feature 002 US3 AC3/SC-008: the backend independently enforces authorization regardless of
what the frontend displays - a Citizen cannot reach an Admin-only endpoint by bypassing the
frontend's route guards and calling it directly, even with a valid cookie session."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from tests.helpers import DEFAULT_PASSWORD, seed_user


async def test_citizen_cookie_session_cannot_call_admin_only_endpoint(
    client: AsyncClient, db: DBSession
):
    citizen = seed_user(db, email="citizen@example.com")

    session_resp = await client.post(
        "/auth/session", json={"email": "citizen@example.com", "password": DEFAULT_PASSWORD}
    )
    assert session_resp.status_code == 200

    resp = await client.patch(
        f"/admin/users/{citizen.id}/role",
        json={"role": "admin"},
        headers={"X-CSRF-Token": client.cookies["csrf_token"]},
    )
    assert resp.status_code == 403
