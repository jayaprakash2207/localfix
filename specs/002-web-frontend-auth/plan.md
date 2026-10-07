# Implementation Plan: LocalFix Frontend and Web Authentication

**Branch**: `002-web-frontend-auth` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-web-frontend-auth/spec.md`

## Summary

Build a React SPA consuming the existing Feature 001 FastAPI backend, plus the explicit backend extensions the
approved proposal requires: a cookie-establishing login endpoint, dual bearer/cookie session resolution,
double-submit-cookie CSRF protection on cookie-authenticated mutations, an Admin-only paginated user-listing
endpoint, real password-reset email delivery behind the existing delivery seam, an explicit fail-closed
`COOKIE_SECURE` setting, and trusted-proxy-aware client-IP resolution for the existing rate limiter. Both
environments (dev via a Vite proxy, production via a reverse proxy) keep frontend and backend same-origin, so
`SameSite=Lax` cookies work identically everywhere with no CORS requirement on the normal path.

## Technical Context

**Language/Version**: Backend: Python 3.12 (unchanged, extending Feature 001's existing codebase). Frontend:
TypeScript 5.x, Node.js 20 LTS (build tooling only — nothing Node-based ships to the browser).

**Primary Dependencies**:
- Backend (additions to Feature 001's existing FastAPI/SQLAlchemy/Alembic/argon2-cffi/uvicorn stack): no new
  heavyweight dependency for cookie/CSRF/trusted-proxy handling (all implemented as small, explicit
  Starlette/FastAPI-native middleware and dependencies, consistent with this codebase's existing pattern of
  hand-rolled services over added libraries — see research.md). Email delivery via Python's standard `smtplib`,
  called synchronously from the existing synchronous seam (see research.md for why SMTP specifically, and why
  no explicit `run_in_threadpool` wrapping is needed given FastAPI's own sync-route dispatch).
- Frontend: React 18, Vite 5, Tailwind CSS 3, TanStack Query 5, React Router (client-side routing — needed for
  role-aware navigation and distinct pages; no heavier framework router required).

**Storage**: PostgreSQL (unchanged — no new tables beyond what Feature 001 already has; the user-listing endpoint
and cookie/CSRF mechanisms read/use existing tables and in-memory request state, not new persisted entities).

**Testing**: Backend: pytest/pytest-asyncio/httpx (unchanged, extended with new test files for the new
endpoints/middleware). Frontend: Vitest + React Testing Library for component/unit tests.

**Target Platform**: Backend: Linux server (unchanged). Frontend: evergreen desktop and mobile browsers (no IE11
or legacy-browser support implied by "modern, responsive" in the spec).

**Project Type**: Web application (frontend + backend) — the first time this repository has both; the existing
backend stays at its current location (`src/`) rather than being moved/renamed, to avoid an unnecessary disruptive
restructure of Feature 001's already-shipped code.

**Performance Goals**: Same as Feature 001 for the backend (no new throughput requirement stated). Frontend:
standard SPA responsiveness — initial route interactive within a few seconds on a typical broadband connection;
no specific Lighthouse/Core-Web-Vitals budget stated in the spec, so none is fabricated here.

**Constraints**: Backend-authoritative security (spec SEC-002/SEC-003) — the frontend duplicates no
authorization logic. Same-origin-only by default (spec Assumptions) — CORS stays off unless explicitly enabled
later. No new infrastructure (no Redis, no message queue, no separate auth service) — CSRF/trusted-proxy/cookie
logic all live inside the existing FastAPI process, consistent with the constitution's Architecture Principles.

**Scale/Scope**: Same scale assumption as Feature 001 (single municipality deployment, low thousands of
accounts) — the admin user-listing endpoint's pagination is sized for this, not for an internet-scale user base.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Gate | Status |
|---|---|---|
| I. Security First | AuthN/Z, input validation, secure data handling must be designed in. | PASS — cookie is HttpOnly/Secure(configurable)/SameSite=Lax; CSRF closes the new attack surface the cookie itself introduces; trusted-proxy allow-list prevents IP-spoofing; `COOKIE_SECURE` fails closed in production (spec BE-012/013, SEC-005/006). |
| II. Role-Based Authorization | Each role reaches only its permitted functionality. | PASS — unchanged backend enforcement (`require_role`); frontend role-based nav is explicitly documented as non-authoritative (spec FE-009, SEC-003), re-verified by SC-008's "bypass the frontend" test requirement. |
| III. Human Accountability for AI | N/A for this feature (no AI-driven decisions here), same as Feature 001. | PASS (N/A), unchanged. |
| IV. Testable Business Rules | Critical rules/transitions must be automated-test-covered. | PASS — spec SC-001–SC-010 are all independently testable; §13 of the approved proposal (carried into this plan's testing strategy) enumerates the exact new test surfaces (dual-transport auth, CSRF enforcement/exemption, pagination, trusted-proxy middleware, cookie fail-closed validation). |
| V. Auditability | Security-sensitive actions must be auditable. | PASS — no new audit-relevant action types are introduced (role/status changes already audited by Feature 001); the new `GET /admin/users` is read-only and doesn't need its own audit entries. |
| Architecture Principles | Modular monolith; no microservices without justification. | PASS — the frontend is a client application, not a service; it does not count against "no microservices." The backend gains no new service, no new infrastructure dependency (CSRF/trusted-proxy/cookie logic are in-process). |
| Development Principles | Readability, maintainability, avoid unnecessary complexity. | PASS — reusing existing patterns (hand-rolled middleware matching the existing `rate_limit_service.py`/`login_attempt` style) rather than introducing a session-management or CSRF library for a handful of straightforward checks. |
| Security and Privacy | Secrets not committed; collect only necessary data. | PASS — SMTP credentials and `TRUSTED_PROXY_IPS`/`COOKIE_SECURE` are environment-config, same mechanism as every existing secret in this codebase; the new user-listing endpoint returns only already-public-elsewhere fields. |
| Testing | Business-critical functionality, authorization, security-sensitive functionality must be tested. | PASS — see Testable Business Rules row; frontend testing (Vitest/RTL) covers component-level loading/error/empty-state requirements (spec FE-015, SC-009). |

No violations requiring justification; Complexity Tracking table is not needed.

**Post-Design Re-check** (after Phase 1 research.md, data-model.md, contracts/, quickstart.md): re-evaluated
against the concrete design — zero new database tables (data-model.md), CSRF verification requiring no
server-side storage, trusted-proxy handling implemented as in-process middleware requiring no new
infrastructure, email delivery via stdlib `smtplib` requiring no new vendor dependency. All gates above remain
**PASS** with no new violations introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/002-web-frontend-auth/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/                             # EXISTING Feature 001 backend — stays in place, extended in place
├── api/
│   ├── auth.py                    # CHANGED: adds POST /auth/session; logout gains cookie-clear + CSRF check
│   ├── admin.py                   # CHANGED: adds GET /admin/users; role/status endpoints gain CSRF check
│   ├── dependencies.py            # CHANGED: get_current_user resolves cookie as well as bearer; new CSRF
│   │                               #   dependency; new trusted-proxy-aware client-IP resolution
│   └── schemas.py                 # CHANGED: adds UserListResponse/UserListItem request/response models
├── application/
│   ├── auth_service.py            # CHANGED: web-session issuance variant (no raw token returned)
│   ├── user_query_service.py      # NEW: search/filter/paginate logic backing GET /admin/users
│   └── csrf_service.py            # NEW: CSRF token issuance/verification
├── infrastructure/
│   ├── config.py                  # CHANGED: adds COOKIE_SECURE (required, fail-closed), TRUSTED_PROXY_IPS
│   ├── email.py                   # CHANGED: real SMTP send replaces the log-only stub
│   └── security/
│       └── trusted_proxy.py       # NEW: ASGI middleware rewriting client IP only from trusted peers
└── main.py                        # CHANGED: wires the trusted-proxy middleware; startup fail-closed check

frontend/                        # NEW
├── src/
│   ├── pages/                     # Landing, Login, Register, ForgotPassword, ResetPassword, Dashboard,
│   │                               #   Profile, admin/Users, admin/AuditLog
│   ├── components/                # Shared UI: nav, form controls, loading/error/empty-state primitives
│   ├── api/                       # Typed fetch client (credentials: "include", CSRF header injection,
│   │                               #   centralized 401/403/429 handling)
│   ├── auth/                      # Small auth-context layer (current user + isAuthenticated only)
│   └── routes/                    # Role-aware route guards (UX convenience, not a security boundary)
├── public/
└── tests/                         # Vitest + React Testing Library

tests/                           # EXISTING backend test tree, extended
├── contract/                      # NEW: test_auth_session.py, test_admin_users.py, test_csrf.py
├── integration/                   # NEW: dual-transport auth, cookie-clear-on-logout, trusted-proxy behavior,
│                                   #   cookie-secure fail-closed startup, real-email-delivery (test double)
└── unit/                          # NEW: csrf_service, user_query_service, trusted_proxy middleware
```

**Structure Decision**: Web application with two top-level trees: the existing `src/` backend (extended in
place, no restructure) and a new sibling `frontend/` directory. This matches the plan template's "web
application" option while respecting that Feature 001's backend already has a working, tested layout that
should not be disrupted just to fit a generic `backend/` naming convention.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A — no Constitution Check violations were identified; this table is intentionally empty.
