"""spec.md User Story 3, Acceptance Scenarios 1-3."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_user_can_only_ever_see_their_own_profile(client: AsyncClient, db: DBSession):
    token_a = await register_and_login(client, "usera@example.com")
    await register_and_login(client, "userb@example.com")
    user_b = db.query(UserAccount).filter(UserAccount.email == "userb@example.com").one()

    # /users/me always returns the caller's own data - there is no id parameter to manipulate.
    me = await client.get("/users/me", headers=auth_headers(token_a))
    assert me.json()["email"] == "usera@example.com"

    # No non-admin endpoint accepts a target user id at all, so "guessing" User B's id has
    # nothing to attach to; confirm the only id-taking routes are admin-gated and reject A.
    guess_role = await client.patch(
        f"/admin/users/{user_b.id}/role", json={"role": "officer"}, headers=auth_headers(token_a)
    )
    assert guess_role.status_code == 403

    guess_status = await client.patch(
        f"/admin/users/{user_b.id}/status", json={"status": "disabled"}, headers=auth_headers(token_a)
    )
    assert guess_status.status_code == 403

    # Even a syntactically valid but non-existent id is still rejected at the role check
    # (403), never reaching a lookup that could leak existence information to a non-admin.
    random_id = uuid.uuid4()
    random_attempt = await client.patch(
        f"/admin/users/{random_id}/status", json={"status": "disabled"}, headers=auth_headers(token_a)
    )
    assert random_attempt.status_code == 403
