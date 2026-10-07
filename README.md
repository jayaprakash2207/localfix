# LocalFix

**A civic-services authentication and administration platform** — FastAPI backend, React web
frontend, built end-to-end with Spec-Driven Development.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)
![Tests](https://img.shields.io/badge/backend_tests-135_passing-brightgreen)
![Tests](https://img.shields.io/badge/frontend_tests-34_passing-brightgreen)
![License](https://img.shields.io/badge/license-unlicensed-lightgrey)

LocalFix provides secure registration, login, session management, and Admin-governed
role/account administration for three roles — **Citizen**, **Officer**, and **Admin** — behind
both a traditional bearer-token API and a cookie-based web frontend, with real email delivery,
CSRF protection, and a full security audit trail.

---

## Contents

- [Highlights](#highlights)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Running the tests](#running-the-tests)
- [Security posture](#security-posture)
- [Production deployment notes](#production-deployment-notes)
- [Project structure](#project-structure)
- [Documentation](#documentation)
- [How this was built](#how-this-was-built)

---

## Highlights

**Authentication & sessions**
- Dual-transport sessions: existing `Authorization: Bearer` API clients are completely
  unaffected; browsers get an `HttpOnly`, cookie-based session that never exposes the raw
  token to JavaScript
- Argon2id password hashing, opaque server-revocable session tokens (never JWT), per-account
  brute-force lockout, and a login-timing side channel closed with constant-cost dummy hashing
- Double-submit-cookie CSRF protection on every cookie-authenticated mutation, with no
  server-side storage — bearer-authenticated requests are correctly exempt

**Administration**
- Admin user management: search, role/status filters, pagination, role changes, and
  account enable/disable — all backend-enforced regardless of what the UI shows
- A last-ACTIVE-Admin invariant that makes it impossible to ever end up with zero Admins,
  closed against a TOCTOU race with row-level locking
- A full, queryable security audit trail (actor, action, affected user, timestamp) for every
  sensitive action

**Production-readiness**
- `COOKIE_SECURE` has no default and **fails closed**: the app refuses to start in production
  with an insecure cookie configuration
- An explicit `TRUSTED_PROXY_IPS` allow-list so the rate limiter identifies real client IPs
  correctly behind a reverse proxy, never trusting a forwarded header from an unconfigured
  source
- Real SMTP password-reset email delivery, same-origin frontend/backend architecture in both
  development (Vite proxy) and production (reverse proxy) — no CORS required

**Quality**
- 135 backend tests, 34 frontend tests, test-first on every task, zero regressions across two
  full feature cycles
- A formal security review pass (13 findings, all remediated) and two Spec-Kit "convergence"
  passes that closed real gaps between spec and implementation

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Argon2id (`argon2-cffi`), uvicorn |
| Database | PostgreSQL |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, React Router, TanStack Query |
| Testing | pytest + httpx (backend), Vitest + React Testing Library (frontend) |
| Tooling | `uv` (Python), `npm` (Node), `ruff` (lint/format), `oxlint` (frontend lint) |

## Architecture

```text
Development                                Production
───────────                                ──────────
Browser                                    Browser
  │                                          │
  ▼                                          ▼
Vite dev server (:5173)                    HTTPS reverse proxy
  │  same-origin proxy, /api/* →             │  same public origin
  ▼                                          ▼
FastAPI backend (:8000) ────────────────── FastAPI backend + static frontend build
  │
  ▼
PostgreSQL
```

Same-origin on both sides means `SameSite=Lax` cookies work identically everywhere — no CORS
configuration needed on the normal path. The backend is a layered modular monolith:

```text
src/
├── api/              presentation — routes, request/response schemas, auth dependencies
├── application/       business logic — auth, CSRF, rate limiting, role/status rules
├── domain/            framework-free types (Role, AccountStatus, …)
└── infrastructure/    data access, security (hashing, tokens, trusted-proxy), email, config
```

## Getting started

```bash
uv venv .venv
uv pip install -e ".[dev]" --python .venv/Scripts/python.exe   # Windows
# uv pip install -e ".[dev]" --python .venv/bin/python          # macOS/Linux
```

Copy `.env.example` to `.env` and point `DATABASE_URL` (and `TEST_DATABASE_URL`) at a PostgreSQL
instance — either `docker compose up -d` (uses `docker-compose.yml`) or a local PostgreSQL install.

**Migrate the database:**

```bash
.venv/Scripts/alembic.exe upgrade head
```

Run the same command with `DATABASE_URL` pointed at your test database too (the test suite reads
`TEST_DATABASE_URL`, falling back to `DATABASE_URL` if unset).

**Seed the first Admin** — the last-ACTIVE-Admin invariant means the API can never create the
first one; every role/status change requires an already-authenticated Admin:

```bash
.venv/Scripts/python.exe scripts/seed_admin.py admin@example.com <password>
```

**Run the backend:**

```bash
.venv/Scripts/uvicorn.exe src.main:app --reload
```

**Run the frontend** (in a second terminal — proxies `/api/*` to the backend above):

```bash
cd frontend
npm install
npm run dev
```

## Running the tests

```bash
# Backend
.venv/Scripts/python.exe -m pytest

# Frontend
cd frontend && npm test
```

Backend tests truncate all tables before each test and run against a real PostgreSQL database
(`TEST_DATABASE_URL`/`DATABASE_URL`), not SQLite — see `specs/001-auth-rbac/research.md` for why.

## Security posture

| Concern | How it's handled |
|---|---|
| Password storage | Argon2id, independently salted per hash |
| Session tokens | Opaque, `secrets.token_urlsafe(32)`, SHA-256 hashed at rest, never JWT |
| Timing side channels | Constant-cost dummy hash on a non-existent account, so login timing can't reveal account existence |
| Brute force | Per-account lockout (5 failures → 15 min), checked before password verification |
| CSRF | Double-submit cookie, enforced only on cookie-authenticated mutations |
| Cookie security | `COOKIE_SECURE` required, no default, fails closed in production |
| Reverse-proxy spoofing | `TRUSTED_PROXY_IPS` allow-list; forwarded headers from untrusted peers are ignored entirely |
| Authorization | Backend-enforced on every request; frontend role-based UI is a convenience only |
| Auditability | Every sensitive action (login, logout, role/status change, password reset) is logged with actor, action, affected user, and timestamp |

## Production deployment notes

`COOKIE_SECURE=true` is a hard requirement for any production deployment
(`ENVIRONMENT=production`) — the app refuses to start otherwise. See `.env.example`.

Set `TRUSTED_PROXY_IPS` (comma-separated) to the real address(es) of the reverse proxy in front
of this app. Leaving it unset is fail-closed: the rate limiter falls back to keying on the
proxy's own address, meaning every client behind it shares one rate-limit bucket. The reverse
proxy itself must **append** the real client address as a new, rightmost `X-Forwarded-For`
entry — never relay a client-supplied header verbatim. See
`src/infrastructure/security/trusted_proxy.py`.

## Project structure

```text
src/                          FastAPI backend (Feature 001, extended by Feature 002)
├── api/                        routes, schemas, auth/CSRF dependencies
├── application/                auth, CSRF, rate-limit, role/status, user-query services
├── domain/                     Role, AccountStatus, and other framework-free types
└── infrastructure/             db models/session, security (hashing, tokens, trusted-proxy), email, config

frontend/                     React web frontend (Feature 002)
├── src/
│   ├── pages/                   Landing, Login, Register, Dashboard, Profile, admin/*
│   ├── components/               AppShell, LoadingState/ErrorState/EmptyState, BasicDashboard
│   ├── api/                      typed fetch client (cookies, CSRF header, 401/403 handling)
│   ├── auth/                     auth context (current user only, never a raw token)
│   └── routes/                   route guards (UX convenience, not a security boundary)
└── tests/                       Vitest + React Testing Library

tests/                        Backend test suite (contract / integration / unit)
specs/                        Spec-Driven Development artifacts (spec, plan, tasks, research)
docs/                         Development session transcript
```

## Documentation

### Feature 001 — Authentication and RBAC

| | |
|---|---|
| Specification | [`specs/001-auth-rbac/spec.md`](specs/001-auth-rbac/spec.md) |
| Plan | [`specs/001-auth-rbac/plan.md`](specs/001-auth-rbac/plan.md) |
| Data model | [`specs/001-auth-rbac/data-model.md`](specs/001-auth-rbac/data-model.md) |
| API contract | [`specs/001-auth-rbac/contracts/auth-api.md`](specs/001-auth-rbac/contracts/auth-api.md) |
| Validation scenarios | [`specs/001-auth-rbac/quickstart.md`](specs/001-auth-rbac/quickstart.md) |
| Task breakdown | [`specs/001-auth-rbac/tasks.md`](specs/001-auth-rbac/tasks.md) |

### Feature 002 — Web Frontend and Web Authentication

| | |
|---|---|
| Specification | [`specs/002-web-frontend-auth/spec.md`](specs/002-web-frontend-auth/spec.md) |
| Plan | [`specs/002-web-frontend-auth/plan.md`](specs/002-web-frontend-auth/plan.md) |
| Data model | [`specs/002-web-frontend-auth/data-model.md`](specs/002-web-frontend-auth/data-model.md) |
| API contract | [`specs/002-web-frontend-auth/contracts/frontend-auth-api.md`](specs/002-web-frontend-auth/contracts/frontend-auth-api.md) |
| Validation scenarios | [`specs/002-web-frontend-auth/quickstart.md`](specs/002-web-frontend-auth/quickstart.md) |
| Task breakdown | [`specs/002-web-frontend-auth/tasks.md`](specs/002-web-frontend-auth/tasks.md) |
| Frontend app docs | [`frontend/README.md`](frontend/README.md) |

## How this was built

This project was built end-to-end using GitHub's [Spec Kit](https://github.com/github/spec-kit)
Spec-Driven Development workflow — specify → clarify/plan → tasks → implement → converge,
repeated per feature, with a formal security review pass after Feature 001.

- [**DEVELOPMENT_LOG.md**](DEVELOPMENT_LOG.md) — a narrative account of both features: design
  decisions, real bugs found and fixed, and what each convergence pass caught
- [**docs/conversation-transcript.md**](docs/conversation-transcript.md) — the raw development
  session transcript
