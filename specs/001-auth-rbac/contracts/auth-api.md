# Phase 1 API Contract: Authentication and Role-Based Access Control

REST/JSON contract exposed by the FastAPI service. All endpoints are backend-enforced per FR-011: identical
authorization checks apply no matter which client calls them. Error responses below are representative shapes;
exact status-code/body conventions can be refined during implementation as long as they remain consistent and
do not leak sensitive detail (e.g., FR-020's "don't disclose disabled vs. wrong password").

Auth is via a session token (research.md: opaque, server-side). Convention used below: `Authorization: Bearer
<token>` header on authenticated requests. `role` on every account is one of `citizen | officer | admin`.

## Public (unauthenticated) endpoints

### POST /auth/register

- **Request**: `{ "email": string, "password": string }`
- **Behavior**: Creates a `UserAccount` with `role=citizen`, `status=active` (FR-001, FR-002). Any `role` field
  in the request body is ignored (FR-003).
- **Responses**:
  - `201` → `{ "id": uuid, "email": string, "role": "citizen" }` (no password field, ever — FR-017)
  - `409` → email already registered (User Story 1, Scenario 4)
  - `422` → validation error (malformed email, weak/missing password)

### POST /auth/login

- **Request**: `{ "email": string, "password": string }`
- **Behavior**: Verifies credentials, account `status=active`, and that the account is not currently locked out
  (FR-005, FR-020, FR-022). On success, creates a `Session` and resets `LoginAttemptRecord.consecutive_failures`
  to 0 (FR-022a). On failure, increments `consecutive_failures` and sets `locked_until` once the 5th consecutive
  failure is reached (FR-022).
- **Responses**:
  - `200` → `{ "session_token": string, "expires_at": datetime }`
  - `401` → invalid credentials, disabled account, or locked-out account — **same generic body in all three
    cases** (FR-020): `{ "error": "invalid_credentials" }`

### POST /auth/password-reset/request

- **Request**: `{ "email": string }`
- **Behavior**: If the email matches an account, creates a `PasswordResetRequest`, invalidates any prior
  unused request for that account, and emails the single-use link. If it does not match, does nothing
  observable (FR-010b).
- **Responses**:
  - `202` → `{ "message": "If that email is registered, a reset link has been sent." }` (identical for both
    matched and unmatched email — FR-010b)

### POST /auth/password-reset/confirm

- **Request**: `{ "token": string, "new_password": string }`
- **Behavior**: Validates the token against `PasswordResetRequest` (unused, unexpired); on success, updates
  `password_hash` and marks the request used (FR-010, FR-010a).
- **Responses**:
  - `200` → `{ "message": "Password updated." }`
  - `400` → token invalid, expired, or already used

## Authenticated endpoints (any role)

### POST /auth/logout

- **Auth**: Bearer session token.
- **Behavior**: Revokes the presented session (`revoked_at = now()`), FR-006.
- **Responses**: `204`

### GET /users/me

- **Auth**: Bearer session token.
- **Behavior**: Returns the caller's own profile only (FR-007); never another user's data (FR-008).
- **Responses**: `200` → `{ "id": uuid, "email": string, "role": string, "status": string, "created_at": datetime }`
  (no password field)

## Admin-only endpoints

All endpoints below require an authenticated session whose account has `role=admin` (FR-014); any other role
receives `403` (FR-015).

### PATCH /admin/users/{user_id}/role

- **Request**: `{ "role": "citizen" | "officer" | "admin" }`
- **Behavior**: Changes the target account's role (FR-004a). Rejects if `role` is not one of the three valid
  values (FR-004c), if the caller is targeting their own account and the new role is not `admin` (FR-004d), or
  if applying the change would leave zero `ACTIVE` admin accounts (FR-004e). Creates an `AuditRecord` with
  action `ROLE_CHANGED` on success.
- **Responses**:
  - `200` → `{ "id": uuid, "role": string }`
  - `403` → caller is not Admin, or change is a disallowed self-demotion
  - `404` → target `user_id` does not exist
  - `409` → change would remove the last ACTIVE admin
  - `422` → invalid role value

### PATCH /admin/users/{user_id}/status

- **Request**: `{ "status": "active" | "disabled" }`
- **Behavior**: Changes the target account's status (FR-019a). Rejects if the caller is targeting their own
  account (FR-019c), or if disabling would leave zero `ACTIVE` admin accounts (FR-019d). On transition to
  `disabled`, revokes all of that account's active sessions (FR-021). Creates an `AuditRecord` with action
  `ACCOUNT_ENABLED` or `ACCOUNT_DISABLED` on success.
- **Responses**:
  - `200` → `{ "id": uuid, "status": string }`
  - `403` → caller is not Admin, or the target is the caller themself
  - `404` → target `user_id` does not exist
  - `409` → change would remove the last ACTIVE admin
  - `422` → invalid status value

### GET /admin/audit-log

- **Query params** (all optional, combinable):
  - `user_id` (uuid) — only records whose `affected_user_id` matches
  - `action` (string) — only records with this exact action (e.g. `LOGIN_SUCCESS`)
  - `since` (datetime) — only records at/after this timestamp
  - `until` (datetime) — only records at/before this timestamp
- **Behavior**: Returns the most recent 500 matching `AuditRecord` entries, newest first (FR-024, FR-025).
  Never includes password values (FR-026, which holds trivially since `AuditRecord` has no password field).
- **Responses**: `200` → `{ "items": [ { "id": uuid, "actor_user_id": uuid|null, "action": string,
  "affected_user_id": uuid, "occurred_at": datetime, "detail": object|null } ] }`

## Demonstration-only endpoints

These two routes exist solely to prove the generic role-gating mechanism works (spec User Story 2,
FR-012/FR-013); they are not LocalFix business functionality, which is out of this feature's scope
(see spec Assumptions).

### GET /citizen/ping

- **Auth**: Bearer session token; caller's role MUST be `citizen`.
- **Responses**: `200` → `{ "status": "ok", "role": "citizen" }` · `403` for any other role.

### GET /officer/ping

- **Auth**: Bearer session token; caller's role MUST be `officer`.
- **Responses**: `200` → `{ "status": "ok", "role": "officer" }` · `403` for any other role.

## Cross-cutting rules (apply to every endpoint above)

- Every authenticated endpoint MUST re-validate the session per the `Session` validity rule in data-model.md
  (not revoked, not expired, owning account still `ACTIVE`) before evaluating role checks (FR-011, FR-021,
  FR-023).
- No response body, at any endpoint, ever includes `password_hash` or a raw password (FR-017).
- No log line, at any verbosity, ever includes a raw password or `password_hash` (FR-018, FR-026).
- A `422` (request validation failure) at any endpoint returns the same `{ "error": "validation_error" }`
  shape as every other error response — not FastAPI's default verbose `{"detail": [...]}` body, which would
  also echo back the client's submitted field values (security review F8).
- `POST /auth/register` and `POST /auth/password-reset/request` are rate-limited to 5 requests per 15
  minutes per source IP; the 6th+ request in a window returns `429 { "error": "rate_limit_exceeded" }`
  (FR-030, security review F7).
- `password`/`new_password` fields on `POST /auth/register` and `POST /auth/password-reset/confirm` MUST be
  8–128 characters; outside that range the request is rejected with the standard `422` validation shape
  above (FR-028, security review F2/F3).
- Email matching (registration uniqueness and login lookup) is case-insensitive (FR-029, security review F4).
