# Quickstart: LocalFix Frontend and Web Authentication

Validation guide for proving this feature works end-to-end once implemented. See
[data-model.md](./data-model.md) and [contracts/frontend-auth-api.md](./contracts/frontend-auth-api.md) for
field/endpoint details referenced below. Feature 001's own [quickstart.md](../001-auth-rbac/quickstart.md)
remains valid and unaffected for everything this feature doesn't change.

## Prerequisites

- Feature 001's existing prerequisites (Python 3.12 + venv, PostgreSQL migrated, a seeded Admin account).
- This feature's new required configuration set in `.env`: `COOKIE_SECURE` (no default — must be set),
  `TRUSTED_PROXY_IPS` (optional, empty by default), `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD`/
  `SMTP_FROM_ADDRESS` (no default — must be set for password-reset email to work).
- Node.js 20 LTS and a package manager for the `frontend/` app.
- Backend running via `uvicorn src.main:app --reload`; frontend dev server running via the Vite dev command,
  which proxies API paths to the backend so the browser only ever sees one origin (per plan.md's Project
  Structure / the approved same-origin development architecture).

## Automated validation

```bash
pytest tests/unit tests/contract tests/integration   # backend, extended with this feature's new test files
cd frontend && npm test                               # Vitest + React Testing Library
```

## Manual / scripted end-to-end scenarios

### 1. Cookie-based web login (no raw token ever exposed)

```bash
curl -i -c cookies.txt -X POST $BASE/auth/session -d '{"email":"alice@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200, body = {"expires_at": "..."} only - no session_token field.
# Expect a Set-Cookie for session_id (HttpOnly) and a separate Set-Cookie for csrf_token (not HttpOnly).

curl -s -b cookies.txt $BASE/users/me
# Expect 200 - the cookie alone authenticates the request, no Authorization header needed.
```

### 2. Existing bearer authentication is unaffected

```bash
curl -s -X POST $BASE/auth/login -d '{"email":"alice@example.com","password":"Str0ngP@ssw0rd!"}' -H 'Content-Type: application/json'
# Expect 200, body = {"session_token": "...", "expires_at": "..."} - unchanged from Feature 001.

curl -s $BASE/users/me -H "Authorization: Bearer <session_token from above>"
# Expect 200 - identical to Feature 001's behavior, proving nothing broke.
```

### 3. CSRF protection on cookie-authenticated mutations

```bash
# Extract the csrf_token cookie value from cookies.txt, then:
curl -i -b cookies.txt -X POST $BASE/auth/logout
# Expect 403 {"error": "csrf_token_invalid"} - no X-CSRF-Token header sent.

curl -i -b cookies.txt -X POST $BASE/auth/logout -H "X-CSRF-Token: <csrf_token value>"
# Expect 204, and both cookies cleared in the response.

# Repeat the "no header" case using the bearer token from scenario 2 instead of the cookie:
curl -i -X POST $BASE/auth/logout -H "Authorization: Bearer <session_token>"
# Expect 204 with no CSRF header required at all - the exemption is scoped correctly.
```

### 4. Admin user listing: search, filter, paginate

```bash
curl -s "$BASE/admin/users?search=alice&page=1&page_size=20" -H "Authorization: Bearer <admin_token>"
# Expect 200 {"items": [...], "total": N, "page": 1, "page_size": 20}, each item with only id/email/role/status/created_at.

curl -s "$BASE/admin/users?role=officer&status=active" -H "Authorization: Bearer <admin_token>"
# Expect only matching accounts.

curl -s "$BASE/admin/users?page=0" -H "Authorization: Bearer <admin_token>"
# Expect 422 (page below minimum).

curl -s "$BASE/admin/users" -H "Authorization: Bearer <citizen_token>"
# Expect 403.
```

### 5. Trusted-proxy client-IP handling

Not practically demonstrable via a single `curl` call against localhost (it depends on which peer address the
connection arrives from, not the request content). Validate instead via:
- The dedicated unit/integration tests (tasks.md T068–T070) that construct ASGI scopes directly — a trusted peer
  address with both single- and multi-value `X-Forwarded-For` headers, and an untrusted peer address with the
  same headers — asserting the middleware honors only the rightmost value from a trusted peer and ignores the
  header entirely from an untrusted one.
- A deployment-time check: confirm the registration/password-reset-request rate limiter's observed source IPs
  in the audit/application logs match real client addresses, not the reverse proxy's address, after setting
  `TRUSTED_PROXY_IPS` to the proxy's real address in a staging environment.

### 6. `COOKIE_SECURE` fail-closed behavior

```bash
ENVIRONMENT=production COOKIE_SECURE=false uvicorn src.main:app
# Expect immediate startup failure with a clear configuration error - the process must not start.

ENVIRONMENT=production COOKIE_SECURE=true uvicorn src.main:app
# Expect normal startup.

ENVIRONMENT=development COOKIE_SECURE=false uvicorn src.main:app
# Expect normal startup (plain local HTTP development).
```

### 7. Password-reset email, real delivery

```bash
curl -s -X POST $BASE/auth/password-reset/request -d '{"email":"alice@example.com"}' -H 'Content-Type: application/json'
# Expect 202 with the same generic message Feature 001 already returns.
# Unlike Feature 001's quickstart, confirm an actual email arrives at a real (or test-SMTP-capturable) inbox,
# containing the reset link - not just a log line.
```

Follow the link into the frontend's reset-password page, submit a new password, and confirm login with the new
password succeeds while the old password fails — identical to Feature 001's existing reset-flow guarantee, now
reachable end-to-end through a real inbox instead of a log line.

### 8. Role-aware navigation is UX only

Log in as a Citizen through the frontend and confirm no Admin navigation is visible. Then, using the Citizen's
own session cookie directly (bypassing the UI entirely, e.g. via `curl -b cookies.txt`), attempt
`GET /admin/users` and confirm `403` — proving the backend enforces this independently of whatever the frontend
chose to show.

## Definition of done for this quickstart

All eight scenarios above pass manually (or via an equivalent automated suite), the backend's full test suite
(Feature 001's existing tests plus this feature's additions) passes with zero regressions, and the frontend's
Vitest suite passes — satisfying spec Success Criteria SC-001 through SC-010.
