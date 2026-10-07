from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_audit_log_returns_items_without_passwords(client: AsyncClient, admin_token: str):
    await register_and_login(client, "alice@example.com")

    resp = await client.get("/admin/audit-log", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    for item in body["items"]:
        assert "password" not in item
        assert "password_hash" not in item


async def test_audit_log_forbidden_for_non_admin(client: AsyncClient):
    citizen_token = await register_and_login(client, "citizen@example.com")
    resp = await client.get("/admin/audit-log", headers=auth_headers(citizen_token))
    assert resp.status_code == 403


async def test_audit_log_filters_by_action_and_user_id(client: AsyncClient, admin_token: str):
    await register_and_login(client, "alice@example.com")
    await register_and_login(client, "bob@example.com")

    all_items = (
        await client.get("/admin/audit-log", headers=auth_headers(admin_token))
    ).json()["items"]
    assert len(all_items) >= 2

    by_action = await client.get(
        "/admin/audit-log", params={"action": "REGISTER"}, headers=auth_headers(admin_token)
    )
    assert by_action.status_code == 200
    assert all(item["action"] == "REGISTER" for item in by_action.json()["items"])

    # Filter down to only the record affecting alice.
    alice_id = next(
        item["affected_user_id"] for item in all_items if item["action"] == "REGISTER"
    )
    by_user = await client.get(
        "/admin/audit-log", params={"user_id": alice_id}, headers=auth_headers(admin_token)
    )
    assert by_user.status_code == 200
    assert all(item["affected_user_id"] == alice_id for item in by_user.json()["items"])
    assert len(by_user.json()["items"]) >= 1
