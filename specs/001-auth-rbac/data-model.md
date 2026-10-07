# Phase 1 Data Model: Authentication and Role-Based Access Control

Derived from the spec's Key Entities, with concrete fields/types/relationships/validation for the chosen
PostgreSQL + SQLAlchemy stack. Field names are illustrative; exact naming may be refined during implementation
without changing the relationships or rules below.

## UserAccount

Represents a registered person (spec: "User Account").

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | Server-generated. |
| email | citext / case-insensitive text, UNIQUE, NOT NULL | Account identifier for registration/login (research.md). |
| password_hash | text, NOT NULL | Argon2id hash only; never plaintext (FR-016). |
| role | enum(Role), NOT NULL, default `CITIZEN` | See Role enum below (FR-002, FR-003). |
| status | enum(AccountStatus), NOT NULL, default `ACTIVE` | See AccountStatus enum below (FR-019). |
| display_name / profile fields | text, nullable | Minimal profile data visible only to the owner (FR-007). Exact fields beyond email are not specified by the spec; kept minimal. |
| created_at | timestamptz, NOT NULL | Set at registration. |
| updated_at | timestamptz, NOT NULL | Set on any mutation (role/status/password/profile change). |

**Validation rules**:
- `email` must be a syntactically valid, unique email address (FR-001; registration rejects duplicates per User
  Story 1 Acceptance Scenario 4).
- `role` on creation is always `CITIZEN` regardless of client input (FR-002, FR-003); only mutable afterward via
  the role-change rules below.
- `password_hash` is never included in any serialized representation returned by the API (FR-017) or written to
  logs (FR-018).

**State transitions**:
- `status`: `ACTIVE → DISABLED` and `DISABLED → ACTIVE`, Admin-only (FR-019a), never self-targeted (FR-019c), and
  never allowed if it would leave zero `ACTIVE` accounts with `role = ADMIN` (FR-019d).
- `role`: any value → any of `CITIZEN|OFFICER|ADMIN`, Admin-only (FR-004a, FR-004b), never self-targeted away
  from `ADMIN` by the acting Admin (FR-004d), and never allowed if it would leave zero `ACTIVE` accounts with
  `role = ADMIN` (FR-004e).

## Role (enum)

`CITIZEN | OFFICER | ADMIN` — exactly one value per `UserAccount` at any time (spec Key Entity "Role"). Invariant
enforced at the application layer (and ideally also as a DB-level check/constraint): at least one `UserAccount`
with `role = ADMIN` and `status = ACTIVE` must exist at all times.

## AccountStatus (enum)

`ACTIVE | DISABLED`.

## Session

Represents an authenticated login instance (spec Key Entity "Session").

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → UserAccount.id), NOT NULL | Owning account. |
| token_hash | text, UNIQUE, NOT NULL | Hash of the opaque session token (raw token given to client only once, at login). |
| created_at | timestamptz, NOT NULL | |
| expires_at | timestamptz, NOT NULL | Fixed duration from creation; exact duration is a configuration value (deferred per spec Assumptions). |
| revoked_at | timestamptz, nullable | Set on explicit logout (FR-006) or when the owning account transitions to `DISABLED` (FR-021). |

**Validity rule**: a session grants access only if `revoked_at IS NULL AND now() < expires_at AND
UserAccount.status = ACTIVE`. Any other state is treated as invalid (FR-021, FR-023, User Story 4).

## PasswordResetRequest

Represents an in-progress, single-use password reset (spec Key Entity "Password Reset Request").

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → UserAccount.id), NOT NULL | |
| token_hash | text, UNIQUE, NOT NULL | Hash of the single-use link token emailed to the user; raw token never persisted. |
| created_at | timestamptz, NOT NULL | |
| expires_at | timestamptz, NOT NULL | Exact duration deferred to implementation configuration (spec Assumptions). |
| used_at | timestamptz, nullable | Set once the reset is completed; a used request can never be reused (FR-010a). |

**Validity rule**: a reset request is usable only if `used_at IS NULL AND now() < expires_at`. FR-010a also
requires that issuing a new request for the same `user_id` invalidates any previously outstanding, unused
request for that user (implemented by marking prior unused rows expired/superseded when a new one is created).

**Privacy rule**: requesting a reset for an email that does not match any `UserAccount` MUST still return the
same response and MUST NOT create a row or send an email (FR-010b).

## LoginAttemptRecord

Tracks consecutive failed logins per account to drive lockout (spec Key Entity "Login Attempt Record").

| Field | Type | Notes |
|---|---|---|
| user_id | UUID (PK, FK → UserAccount.id) | One row per account. |
| consecutive_failures | integer, NOT NULL, default 0 | Incremented on each failed login; reset to 0 on success (FR-022a). |
| locked_until | timestamptz, nullable | Set when `consecutive_failures` reaches 5 (FR-022); cleared (or simply checked against `now()`) once elapsed. |

**Validity rule**: a login attempt for an account is rejected outright (independent of credential correctness)
while `locked_until IS NOT NULL AND now() < locked_until` (FR-022).

## AuditRecord

Represents a logged security-sensitive event (spec Key Entity "Audit Record").

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| actor_user_id | UUID (FK → UserAccount.id), nullable | Null for unauthenticated actions (e.g., anonymous failed login, registration) per FR-025 ("system"/"unauthenticated"). |
| action | text, NOT NULL | One of: `REGISTER`, `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`, `ACCOUNT_ENABLED`, `ACCOUNT_DISABLED`, `ROLE_CHANGED` (FR-024). |
| affected_user_id | UUID (FK → UserAccount.id), NOT NULL | The account the action concerns (may equal `actor_user_id`, e.g., logout). |
| occurred_at | timestamptz, NOT NULL | |
| detail | jsonb, nullable | Non-secret contextual detail only (e.g., previous/new role); MUST NOT contain password values in any form (FR-026). |

## Entity relationship summary

```text
UserAccount (1) ──< (0..N) Session
UserAccount (1) ──< (0..N) PasswordResetRequest
UserAccount (1) ── (0..1) LoginAttemptRecord
UserAccount (1) ──< (0..N) AuditRecord   [as actor_user_id, nullable]
UserAccount (1) ──< (1..N) AuditRecord   [as affected_user_id]
```

## Cross-entity invariant (last-ACTIVE-Admin)

Enforced in the `role_service` and `account_status_service` application-layer code (research.md) at the moment
a role-change or status-change request is evaluated:

```text
COUNT(UserAccount WHERE role = ADMIN AND status = ACTIVE) >= 1
```

Any role-change or disable action that would violate this invariant after being applied MUST be rejected
(FR-004e, FR-019d).
