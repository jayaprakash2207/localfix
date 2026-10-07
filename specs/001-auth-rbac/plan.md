# Implementation Plan: Authentication and Role-Based Access Control

**Branch**: `001-auth-rbac` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-auth-rbac/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Build a backend-only authentication and role-based access control service for LocalFix: registration, login,
logout, self-profile viewing, and self-service password reset, with three roles (Citizen, Officer, Admin) whose
boundaries are enforced entirely server-side. Admins manage role assignment and account enable/disable (never
self-targeted in ways that would remove the last Admin or self-disable). Security controls include Argon2id
password hashing, per-account brute-force lockout, server-revocable sessions with expiration, and an audit trail
for all security-sensitive actions.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (ORM), Alembic (migrations), argon2-cffi (password
hashing), uvicorn (ASGI server)

**Storage**: PostgreSQL

**Testing**: pytest, pytest-asyncio, httpx.AsyncClient (ASGI contract/integration tests against FastAPI), dedicated
test PostgreSQL database for integration tests

**Target Platform**: Linux server (containerized)

**Project Type**: web-service (single backend project, no frontend in scope for this feature)

**Performance Goals**: Standard interactive web-API responsiveness (p95 < 300ms for auth endpoints under modest
load); no high-throughput requirement stated in the spec.

**Constraints**: Backend-only authorization enforcement (spec FR-011); modular monolith per constitution
Architecture Principles — no microservices or extra infrastructure (e.g., caches, message queues) unless a
specific requirement justifies the complexity; passwords/secrets never logged or returned (FR-016–FR-018,
FR-026).

**Scale/Scope**: Single municipality-scale deployment; no specific user-count target given in the spec. Assumed
moderate scale (low thousands of accounts) sufficient for a single PostgreSQL instance with no sharding/caching
layer.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Gate | Status |
|---|---|---|
| I. Security First | AuthN/Z, input validation, secure data handling, protection against common web vulnerabilities must be designed in, not bolted on. | PASS — Argon2id hashing, backend-only authz checks, Pydantic input validation at every endpoint, no secrets in responses/logs (FR-016–FR-018, FR-026). |
| II. Role-Based Authorization | Citizens/Officers/Admins must only reach functionality their role permits. | PASS — every protected route depends on a server-side role check (FR-012–FR-015); no client-trusted role data. |
| III. Human Accountability for AI | AI must not have final authority over important civic decisions; humans must be able to override. | PASS (N/A for this feature) — this feature contains no AI-driven classification or decision support; it is pure authN/authZ plumbing. Revisit if a future feature adds AI-assisted account actions. |
| IV. Testable Business Rules | Critical rules/state transitions must be automated-test-covered and independently verifiable. | PASS — spec FR-027 mandates coverage for auth, authz, role protection, account status, and security rules; Phase 1 contracts and quickstart scenarios map directly to acceptance scenarios. |
| V. Auditability | Security-sensitive admin/security actions must be auditable with actor, action, resource, timestamp. | PASS — dedicated `audit_records` table (data-model.md) satisfies FR-024–FR-026. |
| Architecture Principles | Modular monolith; clear presentation/application/data-access/infrastructure separation; no microservices without justification. | PASS — single FastAPI project with `api/` (presentation), `application/` (business logic), `infrastructure/db` (data access), `infrastructure/security`+`infrastructure/config` (infrastructure); see Project Structure. No additional services introduced. |
| Development Principles | Readability, maintainability, modularity, testability, meaningful naming, appropriate documentation; avoid unnecessary complexity. | PASS — layered structure keeps concerns isolated; no speculative abstractions added beyond what the spec requires. |
| Security and Privacy | Secrets not committed; environment/secret-management for credentials; collect only necessary data. | PASS — DB credentials and any signing/secret values are read from environment configuration (`infrastructure/config.py`), never hard-coded or committed; only email + password + role/status fields are collected, matching spec scope. |
| Testing | Business-critical functionality, API behavior, authorization rules, state transitions, security-sensitive functionality must be tested. | PASS — Phase 1 contracts plus `tests/contract`, `tests/integration`, `tests/unit` directories (Project Structure) are scoped to cover exactly these areas per FR-027. |

No violations requiring justification; Complexity Tracking table is not needed.

**Post-Design Re-check** (after Phase 1 research.md, data-model.md, contracts/, quickstart.md): All gates above
were re-evaluated against the concrete design artifacts (session table instead of unrevokable JWTs, per-account
DB-tracked lockout instead of an added cache service, layered `src/` structure, audit table covering every
required action) and remain **PASS** with no new violations introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/001-auth-rbac/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── api/                      # Presentation layer: FastAPI routers, request/response schemas
│   ├── auth.py                 # register, login, logout, password-reset request/confirm
│   ├── users.py                 # GET /users/me
│   └── admin.py                 # role assignment, account enable/disable, audit log read
├── application/              # Application/business-logic layer: use-case services
│   ├── auth_service.py           # registration, login, logout, lockout tracking
│   ├── password_reset_service.py # reset-token issuance/consumption
│   ├── role_service.py           # role-change rules incl. last-admin invariant
│   ├── account_status_service.py # enable/disable rules incl. self-disable + last-admin invariant
│   └── audit_service.py          # audit record creation
├── domain/                   # Framework-free domain types
│   └── models.py                 # Role, AccountStatus enums; domain-level validation rules
├── infrastructure/           # Infrastructure layer
│   ├── db/
│   │   ├── models.py              # SQLAlchemy ORM models (User, Session, PasswordResetRequest, LoginAttemptRecord, AuditRecord)
│   │   ├── session.py             # engine/session factory
│   │   └── migrations/            # Alembic migration scripts
│   ├── security/
│   │   ├── hashing.py             # Argon2id password hashing/verification
│   │   └── tokens.py              # opaque session + reset-link token generation
│   └── config.py                 # environment-based settings (DB URL, lockout/session/reset durations)
└── main.py                   # FastAPI app wiring (routers, DB lifecycle, middleware)

tests/
├── contract/                 # Request/response shape tests per contracts/auth-api.md
├── integration/              # End-to-end flows against a real test DB (register→login→profile, lockout, reset, role/status admin actions, last-admin invariant)
└── unit/                     # Service-level tests (hashing, token validity, lockout counter logic, role/status rule functions)
```

**Structure Decision**: Single backend project (web-service), no frontend in scope. The `src/` tree is organized
by architectural layer — `api/` (presentation), `application/` (business logic/use cases), `domain/` (pure
types/enums), `infrastructure/` (data access + cross-cutting concerns) — directly satisfying the constitution's
Architecture Principles (modular monolith with clear layer separation, no microservices).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A — no Constitution Check violations were identified; this table is intentionally empty.

## Security Hardening Addendum (2026-10-07)

A post-implementation security review (findings F1–F13) identified gaps against the constitution's
Security First principle and this plan's own Testing principle. This addendum records the technical
decisions for the findings being actioned now (F1–F8, F10, F11) without reopening or rewriting the
Technical Context / Constitution Check sections above. Implementation is tracked in tasks.md Phase 15;
F9, F12, F13 are explicitly deferred (see spec.md Assumptions) and have no decisions recorded here.

| Finding | Decision | Rationale |
|---|---|---|
| F1 — login timing oracle | Call `verify_password()` against a fixed dummy Argon2 hash whenever the account doesn't exist, inside `auth_service.login()`. No new dependency. | Equalizes cost between the two branches without touching the response contract (FR-031). |
| F2/F3 — password length | `password`/`new_password` fields gain `min_length=8, max_length=128` in `src/api/schemas.py` (Pydantic-level, rejected as 422 before reaching any service code). | Pydantic field constraints are the cheapest enforcement point and also bound request size for this field, partially addressing the DoS angle of F3. No complexity rules, per decision. |
| F4 — email case-sensitivity | Normalize email to lowercase in `auth_service.py` and `password_reset_service.py` before every query/insert, **plus** a functional unique index on `lower(email)` at the DB layer as defense-in-depth. | App-layer normalization alone is sufficient for correctness; the DB index guards against any future code path that queries/inserts without going through these services. |
| F5 — last-admin TOCTOU race | Add `.with_for_update()` row locking to the active-admin-count query in `role_service.change_role()` and `account_status_service.change_status()`. No new table, no DB constraint/trigger. | Serializes the two concurrent-request scenarios at the row-lock level, inside the existing transaction — no architectural change. |
| F6 — docs exposure | New `environment: Literal["development", "production"] = "development"` setting in `infrastructure/config.py`. `src/main.py` passes `docs_url=None, redoc_url=None, openapi_url=None` to `FastAPI(...)` when `environment == "production"`. | Smallest possible change; reuses the same settings mechanism already used for every other tunable. |
| F7 — rate limiting | New `RateLimitRecord` ORM model + table (`source_ip`, `endpoint`, `window_start`, `request_count`), mirroring the existing `login_attempt_records` pattern. New `src/application/rate_limit_service.py`, wired as a FastAPI dependency on `/auth/register` and `/auth/password-reset/request`. **Explicitly not** Redis/slowapi/any external service. | Matches the constitution's Architecture Principles (no microservices/extra infrastructure without justification) and reuses an already-proven pattern in this codebase. |
| F8 — error shape consistency | Register a custom `RequestValidationError` exception handler in `src/main.py` that maps Pydantic 422s into the existing `{"error": "..."}` contract, replacing FastAPI's default verbose shape. | One handler, no change to any endpoint; `contracts/auth-api.md` gets a corresponding doc update as part of the same task. |
| F10 — dev DSN fallback | Remove the hardcoded default for `database_url` in `infrastructure/config.py` — it becomes a required setting with no fallback, so the app fails fast at startup with a clear error if `.env`/environment variables are missing, instead of silently targeting `localhost:5432`. | Fail-fast is strictly safer than a silent insecure default; no behavior change when correctly configured. |
| F11 — Argon2 exception handling | Widen the caught exception in `hashing.py::verify_password` from `argon2.exceptions.VerifyMismatchError` to **both** `argon2.exceptions.VerificationError` and `argon2.exceptions.InvalidHashError`. | Discovered during implementation that these two do not share a common base class in argon2-cffi (`InvalidHashError` inherits from `ValueError`, not `Argon2Error`) — `VerificationError` alone does not catch a malformed/non-Argon2 hash string, so both must be caught explicitly. No new dependency, no behavior change for the already-tested "wrong password" case. |

### Project Structure additions (Phase 15)

```text
src/
├── application/
│   └── rate_limit_service.py       # NEW — F7: per-source-IP/endpoint rate limiting
├── infrastructure/
│   ├── config.py                    # CHANGED — adds `environment`; removes insecure database_url default
│   └── db/models.py                 # CHANGED — adds RateLimitRecord
└── main.py                          # CHANGED — conditional docs_url/openapi_url; RequestValidationError handler

tests/
├── unit/           # NEW: login-timing call-count test, malformed-hash test
├── contract/        # NEW: password-policy boundaries, docs-exposure-by-environment, rate-limit thresholds, 422-shape consistency
└── integration/     # NEW: email case-insensitivity, last-admin concurrency race
```

No change to the single-backend-project **Structure Decision** itself — all additions stay within the
existing layered `src/` tree; no new service, no new external infrastructure dependency.
