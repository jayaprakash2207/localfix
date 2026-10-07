# Quickstart: Authentication and Role-Based Access Control

Validation guide for proving the feature works end-to-end once implemented. See
[data-model.md](./data-model.md) and [contracts/auth-api.md](./contracts/auth-api.md) for field/endpoint
details referenced below.

## Prerequisites

- Python 3.12 and a virtual environment with the project's dependencies installed (FastAPI, SQLAlchemy,
  Alembic, argon2-cffi, uvicorn, pytest, pytest-asyncio, httpx).
- A running PostgreSQL instance reachable via the configured `DATABASE_URL` (e.g., via `docker compose up db`
  if a compose file is added during implementation).
- Database migrations applied: `alembic upgrade head`.
- At least one seeded `ACTIVE` Admin account (the last-ACTIVE-Admin invariant means the system cannot create
  its first Admin through the API itself — this one row is expected to be seeded out-of-band, e.g., via a
  migration or management script, consistent with spec Assumptions).
- App running locally: `uvicorn src.main:app --reload`.

## Automated validation

```bash
pytest tests/unit            # service-level logic: hashing, lockout counter, role/status rules
pytest tests/contract        # request/response shape per contracts/auth-api.md
pytest tests/integration     # full flows below, against a real test database
```

All three suites must pass before the feature is considered complete (spec SC-009).

## Manual / scripted end-to-end scenarios

Each scenario corresponds to acceptance scenarios in `spec.md`. Replace `$BASE` with the running server URL
(e.g., `http://localhost:8000`).

### 1. Citizen registration and first login (User Story 1)

```bash
curl -s -X POST $BASE/auth/register -d '{"email":"alice@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 201, role "citizen"

curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200, a session_token

curl -s $BASE/users/me -H "Authorization: Bearer <session_token>"
# Expect 200, alice's own profile with role "citizen"
```

Confirm re-registering the same email returns `409` (Scenario 4), and that sending `{"role":"admin"}` in the
register body is ignored — the created account is still `citizen` (Scenario 2).

### 2. Admin role assignment and last-admin invariant (User Story 2a)

```bash
# As the seeded Admin:
curl -s -X PATCH $BASE/admin/users/<alice_id>/role -d '{"role":"officer"}' -H 'Authorization: Bearer <admin_token>' -H 'Content-Type: application/json'
# Expect 200, alice is now "officer"

# As alice (now an officer), attempt to change her own role:
curl -s -X PATCH $BASE/admin/users/<alice_id>/role -d '{"role":"admin"}' -H 'Authorization: Bearer <alice_token>' -H 'Content-Type: application/json'
# Expect 403 (not Admin)

# As the sole seeded Admin, attempt to demote self:
curl -s -X PATCH $BASE/admin/users/<admin_id>/role -d '{"role":"citizen"}' -H 'Authorization: Bearer <admin_token>' -H 'Content-Type: application/json'
# Expect 403 or 409 (self-demotion / last-admin protection)
```

### 3. Role-based access enforcement (User Story 2)

Call an admin-only endpoint (e.g., `PATCH /admin/users/{id}/role`) as a Citizen or Officer token and confirm
`403` in every case, regardless of request origin.

### 4. Protecting other users' information (User Story 3)

As alice, request `GET /users/me` for her own token (succeeds), then attempt any endpoint/parameter that would
return another user's profile — confirm it is rejected or scoped to the caller only (no such endpoint should
exist for non-admins per the contract).

### 5. Logout and session expiration (User Story 4)

```bash
curl -s -X POST $BASE/auth/logout -H "Authorization: Bearer <session_token>"
# Expect 204

curl -s $BASE/users/me -H "Authorization: Bearer <session_token>"
# Expect 401 (session revoked)
```

For expiration, use a test-only short-lived session configuration (per research.md, duration is a config
value) and confirm the same `401` behavior once `expires_at` has passed.

### 6. Password reset (User Story 5)

```bash
curl -s -X POST $BASE/auth/password-reset/request -d '{"email":"alice@example.com"}' -H 'Content-Type: application/json'
# Expect 202 (generic message)

curl -s -X POST $BASE/auth/password-reset/request -d '{"email":"nobody@example.com"}' -H 'Content-Type: application/json'
# Expect 202 with the SAME message, and confirm (via test hook/DB check) no email was sent and no row created

# Using the token delivered to alice's test mailbox/fixture:
curl -s -X POST $BASE/auth/password-reset/confirm -d '{"token":"<token>","new_password":"N3wP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200

# Old password now fails, new password works:
curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 401
curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"N3wP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200

# Reusing the same reset token again:
curl -s -X POST $BASE/auth/password-reset/confirm -d '{"token":"<token>","new_password":"Another1!"}' -H 'Content-Type: application/json'
# Expect 400 (already used)
```

### 7. Account disablement and admin-only status control (User Story 2b, 6)

```bash
# As Admin, disable alice:
curl -s -X PATCH $BASE/admin/users/<alice_id>/status -d '{"status":"disabled"}' -H 'Authorization: Bearer <admin_token>' -H 'Content-Type: application/json'
# Expect 200

# Alice's existing session is now rejected:
curl -s $BASE/users/me -H "Authorization: Bearer <alice_session_token>"
# Expect 401

# Alice cannot log back in even with correct credentials:
curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"N3wP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 401 (generic "invalid_credentials", not distinguishable from a wrong password)

# As Admin, attempt to disable own account:
curl -s -X PATCH $BASE/admin/users/<admin_id>/status -d '{"status":"disabled"}' -H 'Authorization: Bearer <admin_token>' -H 'Content-Type: application/json'
# Expect 403

# As Citizen/Officer, attempt to disable any account:
curl -s -X PATCH $BASE/admin/users/<alice_id>/status -d '{"status":"active"}' -H 'Authorization: Bearer <officer_token>' -H 'Content-Type: application/json'
# Expect 403
```

### 8. Brute-force lockout (User Story 7)

```bash
for i in 1 2 3 4 5; do
  curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"wrong"}' -H 'Content-Type: application/json'
done
# 5th failure should trigger lockout

curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"N3wP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 401 even with the CORRECT password, because the account is locked out

# Wait out the 15-minute cool-down (or use a test-only shortened duration), then retry with correct password:
# Expect 200
```

### 9. Security audit trail (User Story 8)

After running scenarios 1–8, query `GET /admin/audit-log` as Admin and confirm entries exist for: `REGISTER`,
`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`,
`ACCOUNT_DISABLED`, `ROLE_CHANGED` — each with a non-null `occurred_at`, an `affected_user_id`, and no password
values anywhere in the response.

### 10. Password length policy (FR-028, security review F2/F3)

```bash
curl -s -X POST $BASE/auth/register -d '{"email":"short@example.com","password":"abc1234"}' -H 'Content-Type: application/json'
# Expect 422 (7 chars, below the 8-character minimum)

curl -s -X POST $BASE/auth/register -d '{"email":"ok@example.com","password":"abcd1234"}' -H 'Content-Type: application/json'
# Expect 201 (exactly 8 chars)

curl -s -X POST $BASE/auth/register -d "{\"email\":\"toolong@example.com\",\"password\":\"$(python3 -c 'print("a"*129)')\"}" -H 'Content-Type: application/json'
# Expect 422 (129 chars, above the 128-character maximum)
```

### 11. Case-insensitive email (FR-029, security review F4)

```bash
curl -s -X POST $BASE/auth/register -d '{"email":"Carol@Example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 201

curl -s -X POST $BASE/auth/register -d '{"email":"carol@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 409 (same account, different case)

curl -s -X POST $BASE/auth/login -d '{"email":"CAROL@EXAMPLE.COM","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200 (login succeeds regardless of the case used at registration)
```

### 12. Rate limiting on registration and password-reset-request (FR-030, security review F7)

```bash
for i in 1 2 3 4 5; do
  curl -s -X POST $BASE/auth/register -d "{\"email\":\"rl$i@example.com\",\"password\":\"Str0ngP@ssw0rd!\"}" -H 'Content-Type: application/json'
done
# All 5 expect 201

curl -s -X POST $BASE/auth/register -d '{"email":"rl6@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 429 (6th request from the same source IP within 15 minutes)

# Wait out the 15-minute window (or use a test-only shortened duration), then retry:
# Expect 201. The same threshold/window applies independently to POST /auth/password-reset/request.
```

### 13. Login-timing safety (FR-031, security review F1)

Not practically verifiable via manual `curl` timing (network jitter dwarfs the signal this closes). Verified
instead by `tests/unit/test_login_timing_safety.py`, which asserts behaviorally that a login attempt against a
nonexistent email invokes the same password-verification code path (against a fixed dummy hash) that a
wrong-password attempt against a real account does — so both cost the same regardless of account existence.

## Definition of done for this quickstart

All thirteen scenarios above pass manually (or via an equivalent `tests/integration`/`tests/unit` suite), and
the three pytest suites (`unit`, `contract`, `integration`) pass with no failures, satisfying spec Success
Criteria SC-001 through SC-016.
