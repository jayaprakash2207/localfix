# LocalFix — Authentication and Role-Based Access Control

Backend-only FastAPI service implementing Feature 001 (`specs/001-auth-rbac/`): registration, login,
logout, self-profile viewing, password reset, and Admin-governed role/account-status management for
three roles (Citizen, Officer, Admin).

## Setup

```bash
uv venv .venv
uv pip install -e ".[dev]" --python .venv/Scripts/python.exe   # Windows
# uv pip install -e ".[dev]" --python .venv/bin/python          # macOS/Linux
```

Copy `.env.example` to `.env` and point `DATABASE_URL` (and `TEST_DATABASE_URL`) at a PostgreSQL
instance — either `docker compose up -d` (uses `docker-compose.yml`) or a local PostgreSQL install.

## Migrations

```bash
.venv/Scripts/alembic.exe upgrade head
```

Run the same command with `DATABASE_URL` pointed at your test database to migrate it too (the test
suite reads `TEST_DATABASE_URL`, falling back to `DATABASE_URL` if unset).

## Seeding the first Admin

The last-ACTIVE-Admin invariant (spec FR-004e, FR-019d) means the API can never create the first
Admin — every role/status change requires an already-authenticated Admin. Seed one directly:

```bash
.venv/Scripts/python.exe scripts/seed_admin.py admin@example.com <password>
```

## Running the app

```bash
.venv/Scripts/uvicorn.exe src.main:app --reload
```

## Running the tests

```bash
.venv/Scripts/python.exe -m pytest
```

Tests truncate all tables before each test and run against `TEST_DATABASE_URL`/`DATABASE_URL` — use a
real PostgreSQL database, not SQLite (see `specs/001-auth-rbac/research.md` for why).

## Deployment behind a reverse proxy

`COOKIE_SECURE=true` is a hard requirement for any production deployment (`ENVIRONMENT=production`).
The app refuses to start if `ENVIRONMENT=production` and `COOKIE_SECURE` is `false` or unset — see
`.env.example` for details.

Set `TRUSTED_PROXY_IPS` (comma-separated) to the real address(es) of the reverse proxy sitting in
front of this app in production. Leaving it unset is fail-closed — the rate limiter falls back to
keying on the proxy's own address, meaning **every client behind that proxy shares one rate-limit
bucket** (one abusive client can lock out everyone else).

The reverse proxy itself must be configured to **append** the real client address it observed as a
new, rightmost entry in `X-Forwarded-For` — overwriting or discarding any value a client sent
directly — never relaying a client-supplied header verbatim. This middleware (`TrustedProxyMiddleware`,
`src/infrastructure/security/trusted_proxy.py`) trusts only the rightmost entry, and only when the
immediately connecting peer is itself in `TRUSTED_PROXY_IPS`, precisely because a correctly configured
proxy is the one that put that entry there — never a value the client could forge.

## Project layout

See `specs/001-auth-rbac/plan.md` ("Project Structure") for the full layered breakdown
(`src/api` presentation, `src/application` business logic, `src/domain` framework-free types,
`src/infrastructure` data access/security/config).

## Feature documentation

### Feature 001: Authentication and RBAC

- Specification: `specs/001-auth-rbac/spec.md`
- Plan: `specs/001-auth-rbac/plan.md`
- Data model: `specs/001-auth-rbac/data-model.md`
- API contract: `specs/001-auth-rbac/contracts/auth-api.md`
- Manual validation scenarios: `specs/001-auth-rbac/quickstart.md`
- Task breakdown: `specs/001-auth-rbac/tasks.md`

### Feature 002: LocalFix Frontend and Web Authentication

- Specification: `specs/002-web-frontend-auth/spec.md`
- Plan: `specs/002-web-frontend-auth/plan.md`
- Data model: `specs/002-web-frontend-auth/data-model.md`
- API contract: `specs/002-web-frontend-auth/contracts/frontend-auth-api.md`
- Manual validation scenarios: `specs/002-web-frontend-auth/quickstart.md`
- Task breakdown: `specs/002-web-frontend-auth/tasks.md`
- Frontend app: `frontend/` (see `frontend/README.md` for setup/dev/build/test commands)
