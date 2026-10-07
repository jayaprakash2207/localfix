# Phase 0 Research: Authentication and Role-Based Access Control

All Technical Context items were either specified directly by the user or resolved below as explicit decisions.
No `NEEDS CLARIFICATION` markers remain.

## Backend language & framework

- **Decision**: Python 3.12 with FastAPI.
- **Rationale**: User-selected. FastAPI's Pydantic-based request/response validation gives testable, explicit
  schemas at every endpoint (supports constitution's Testable Business Rules principle), and its automatic
  OpenAPI generation doubles as a living artifact for the Phase 1 API contract.
- **Alternatives considered**: Node.js/TypeScript (Express/Fastify) — rejected per user selection in favor of
  Python/FastAPI.

## Persistent storage

- **Decision**: PostgreSQL, accessed via SQLAlchemy 2.0 ORM with Alembic migrations.
- **Rationale**: User-selected. Relational integrity (unique email constraint, foreign keys from
  sessions/reset-requests/audit-records to users) maps naturally onto the spec's Key Entities and their
  relationships; mature migration tooling (Alembic) suits a modular monolith that will evolve over time.
- **Alternatives considered**: SQLite — rejected as it is better suited to local/dev-only use and offers weaker
  concurrent-write guarantees than a production-oriented civic system should rely on.

## Password storage

- **Decision**: Argon2id via `argon2-cffi`.
- **Rationale**: Argon2id is the current OWASP-recommended password hashing algorithm (memory-hard, resistant to
  GPU/ASIC cracking), directly satisfying FR-016 ("one-way, salted cryptographic hash") and the constitution's
  Security First principle.
- **Alternatives considered**: bcrypt — also acceptable and widely used, but Argon2id is preferred under current
  OWASP guidance and has no practical drawback for this project's scale.

## Session mechanism

- **Decision**: Server-side opaque session tokens, persisted in a `sessions` table, rather than stateless JWTs.
- **Rationale**: The spec requires that logout (FR-006) and account disablement (FR-021) immediately invalidate
  a session. A stateless JWT cannot be revoked before its natural expiry without an additional revocation-list
  mechanism; a DB-backed session row can simply be marked invalid/expired and checked on every request, which is
  simpler and maps directly onto the spec's own "Session" key entity (owning account, creation time, expiration
  time, current validity).
- **Alternatives considered**: JWT access/refresh tokens — rejected because satisfying immediate revocation would
  require a parallel revocation-list store, adding complexity the constitution's Architecture Principles caution
  against introducing without a specific justifying requirement.

## Brute-force lockout tracking

- **Decision**: Per-account lockout state tracked in a `login_attempts` table (the spec's "Login Attempt Record"
  entity): consecutive failure count + lockout-until timestamp, checked and updated on every login attempt.
- **Rationale**: Must survive process restarts and work correctly for a single-instance modular monolith without
  introducing an external cache. A DB row per account is sufficient at the stated scale (FR-022, FR-022a).
- **Alternatives considered**: Redis-backed rate limiting — rejected as unjustified additional infrastructure for
  the current scale; would violate the constitution's "no microservices/extra infra without justification"
  guidance.

## Testing approach

- **Decision**: pytest + pytest-asyncio + `httpx.AsyncClient` driving the FastAPI app directly (ASGI transport),
  backed by a real, disposable test PostgreSQL database for integration tests; narrower unit tests for pure
  service-layer logic (hashing, lockout counter transitions, role/status rule functions) with no DB dependency.
- **Rationale**: FR-027 requires automated coverage of authentication, authorization, role protection, account
  status, and the specified security rules. Testing against a real Postgres instance (rather than mocking the
  database or substituting SQLite) exercises the actual uniqueness/foreign-key/locking behavior the design
  relies on, directly satisfying the constitution's Testing principle.
- **Alternatives considered**: Mocking the database layer — rejected because it would not verify the real
  constraints (e.g., unique email, last-admin invariant enforced at the data layer) that the security rules
  depend on.

## Performance, scale, and deployment target

- **Decision**: Standard interactive web-API responsiveness (p95 < 300ms for auth endpoints under modest load);
  Linux container deployment; scale assumed to be low thousands of accounts for a single municipality.
- **Rationale**: The spec sets no explicit throughput/latency targets; these are reasonable, non-blocking
  defaults consistent with "Examples of reasonable defaults" guidance (standard web/mobile app expectations) and
  do not constrain the design choices above.
- **Alternatives considered**: N/A — no competing scale requirement was presented.
