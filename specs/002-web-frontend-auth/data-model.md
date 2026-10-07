# Phase 1 Data Model: LocalFix Frontend and Web Authentication

## Headline fact: zero new database tables, zero new migrations

Every capability in this feature is served by Feature 001's existing five tables
(`user_accounts`, `sessions`, `audit_records`, `login_attempt_records`, `rate_limit_records`) plus new
environment configuration and new request/response shapes. Nothing here requires an Alembic migration.

## Reused entities (unchanged schema)

- **UserAccount** — unchanged. The new `GET /admin/users` endpoint queries it read-only; the existing
  role/status-change endpoints mutate it exactly as Feature 001 already does.
- **Session** — unchanged. `POST /auth/session` creates a row exactly like `POST /auth/login` does today (same
  table, same fields: `id, user_id, token_hash, created_at, expires_at, revoked_at`) — the only difference is
  *transport*: the resulting token's hash is looked up via a cookie instead of (or in addition to) a bearer
  header. No new column, no new table.
- **AuditRecord** — unchanged. No new action types are introduced; role/status changes made through the web UI
  produce the same `ROLE_CHANGED`/`ACCOUNT_ENABLED`/`ACCOUNT_DISABLED` records Feature 001 already writes.
- **RateLimitRecord** — unchanged. Once the trusted-proxy middleware (research.md) corrects
  `request.client.host` for requests arriving through a trusted peer, this table's existing
  `(source_ip, endpoint)` keying works unmodified with the corrected address.
- **LoginAttemptRecord** — unchanged; not touched by this feature at all.

## New request/response shapes (not persisted entities)

- **WebSessionResponse** — returned by `POST /auth/session`: `{expires_at}`. Deliberately omits the raw token
  field present in `LoginResponse` (used by the unchanged `POST /auth/login`), per spec BE-001/SEC-001.
- **UserListQuery** — the shape of an Admin's request to `GET /admin/users`: `{search?, role?, status?, page,
  page_size}`. Not persisted; validated per-request (page ≥ 1, 1 ≤ page_size ≤ 100 — research.md).
- **UserListItem** — one entry in the user-listing response: `{id, email, role, status, created_at}` — identical
  safe-field shape to the existing `UserPublic` schema, reused rather than duplicated.
- **UserListResponse** — `{items: UserListItem[], total, page, page_size}`.

## New configuration (not data; environment-level, operator-provided)

- **`COOKIE_SECURE`** (boolean, **no default** — required). Controls the session cookie's `Secure` attribute.
  Validated at startup: if `environment == "production"` and `COOKIE_SECURE == false`, the application refuses
  to start (spec BE-013).
- **`TRUSTED_PROXY_IPS`** (list of addresses, default empty). Controls which immediate connecting peers the
  trusted-proxy middleware (research.md) will honor `X-Forwarded-For` from. Empty = never honor one, fail-closed
  to today's existing (direct-peer-only) behavior. When honored, only the **rightmost** comma-separated value in
  a multi-value `X-Forwarded-For` is used (research.md) — the header is never treated as a single opaque IP
  string.
- **SMTP configuration** (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`) —
  backs the real email-delivery implementation (research.md); no default, since there is no safe default mail
  server to silently fall back to.

## CSRF token (explicitly not a persisted entity)

The `csrf_token` cookie value is generated fresh at each `POST /auth/session` call and is validated purely by
comparing the request's `X-CSRF-Token` header to the `csrf_token` cookie on the same request — **no server-side
storage or lookup is involved**. This is the standard double-submit-cookie property: proving the header and
cookie match is sufficient to prove the request originated from same-site JavaScript, without the server needing
to remember what value it issued.

## Entity relationship summary (unchanged from Feature 001)

```text
UserAccount (1) ──< (0..N) Session
UserAccount (1) ──< (0..N) AuditRecord   [as actor_user_id and/or affected_user_id]
UserAccount (1) ── (0..1) LoginAttemptRecord
(RateLimitRecord is keyed by source_ip + endpoint, not by UserAccount)
```

No new edges. `GET /admin/users` is a read-only projection over `UserAccount`; it introduces no new
relationship.
