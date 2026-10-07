# Phase 1 API Contract: LocalFix Frontend and Web Authentication

Delta contract against Feature 001's [`contracts/auth-api.md`](../../001-auth-rbac/contracts/auth-api.md), which
remains the source of truth for every endpoint not listed below as new or changed.

## Unchanged (reused exactly as-is)

`POST /auth/register`, `POST /auth/login` (bearer contract, non-browser clients), `POST /auth/password-reset/request`,
`POST /auth/password-reset/confirm`, `GET /users/me`, `GET /admin/audit-log`.

## New

### POST /auth/session

Browser-only login. Internally verifies credentials via the same logic `POST /auth/login` uses (inheriting its
per-account lockout protection automatically — no duplicated brute-force logic).

- **Request**: `{ "email": string, "password": string }`
- **Behavior**: On success, sets two cookies and returns a token-free body:
  - `session_id` cookie: `HttpOnly; SameSite=Lax; Secure={COOKIE_SECURE}; Max-Age=<seconds until Session.expires_at>`
  - `csrf_token` cookie: **not** `HttpOnly` (frontend JS must read it); same `SameSite`/`Secure` policy
- **Responses**:
  - `200` → `{ "expires_at": datetime }` — **no `session_token` field**, unlike `LoginResponse`
  - `401` → `{ "error": "invalid_credentials" }` — identical generic body to `POST /auth/login`'s failure case
    (same non-disclosure guarantee, same lockout interaction)
  - `422` → validation error

### GET /admin/users

Admin-only. Requires the same authorization gate as every other `/admin/*` endpoint (`require_admin`); since
this is a `GET`, it does not require a CSRF token even when cookie-authenticated (CSRF protection applies only
to state-changing methods).

- **Query params** (all optional except pagination defaults):
  - `search` (string) — partial, case-insensitive match against `email`
  - `role` (`citizen | officer | admin`)
  - `status` (`active | disabled`)
  - `page` (int, default `1`, min `1`)
  - `page_size` (int, default `20`, min `1`, max `100`)
- **Responses**:
  - `200` → `{ "items": [ { "id": uuid, "email": string, "role": string, "status": string, "created_at": datetime } ], "total": int, "page": int, "page_size": int }`
  - `403` → caller is not Admin
  - `422` → invalid `role`/`status` value, or `page`/`page_size` out of bounds

## Changed (same path, extended behavior)

### POST /auth/logout

- **Auth**: Bearer token **or** session cookie (whichever authenticated the request).
- **New behavior**: if authenticated via the session cookie, a valid, matching `X-CSRF-Token` header is now
  required (see Cross-cutting rules below); the response additionally clears the `session_id` and `csrf_token`
  cookies. Bearer-authenticated calls are unaffected — no CSRF header required, no cookie to clear.
- **Responses**: `204` (unchanged) · `403` → `{ "error": "csrf_token_invalid" }` (new, cookie-auth only)

### PATCH /admin/users/{user_id}/role

### PATCH /admin/users/{user_id}/status

- **New behavior**: if authenticated via the session cookie, a valid, matching `X-CSRF-Token` header is now
  required. Bearer-authenticated calls are unaffected. All other behavior (role/status validation, self-targeting
  rejection, last-admin invariant) is unchanged from Feature 001.
- **Responses**: existing `200`/`403`/`404`/`409`/`422` (unchanged) · `403` → `{ "error": "csrf_token_invalid" }`
  (new, cookie-auth only — distinguishable from the existing `self_demotion_not_allowed`/
  `self_status_change_not_allowed`/`forbidden` `403` reasons by its `error` value)

## Cross-cutting rules (apply in addition to Feature 001's existing cross-cutting rules)

- Every endpoint now accepts **either** a valid `Authorization: Bearer <token>` header **or** a valid
  `session_id` cookie for authentication; the header is checked first, so any existing bearer-authenticated
  client's behavior is completely unchanged.
- Every cookie-authenticated (not bearer-authenticated) state-changing request (`POST`/`PATCH`/`PUT`/`DELETE`) —
  concretely: `POST /auth/logout`, `PATCH /admin/users/{id}/role`, `PATCH /admin/users/{id}/status`, and any
  future one — **MUST** include a `X-CSRF-Token` header matching the `csrf_token` cookie, or the request is
  rejected with `403 { "error": "csrf_token_invalid" }` before any business logic runs.
- `GET` requests never require a CSRF token, cookie-authenticated or not.
- The raw session token is **never** present in any response body produced by the cookie-based login path
  (`POST /auth/session`); it remains present in `POST /auth/login`'s response body, unchanged, for non-browser
  clients.
