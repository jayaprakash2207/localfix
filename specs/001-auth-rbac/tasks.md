---

description: "Task list for Feature 001: Authentication and Role-Based Access Control"
---

# Tasks: Authentication and Role-Based Access Control

**Input**: Design documents from `/specs/001-auth-rbac/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-api.md, quickstart.md (all present)

**Tests**: Included and REQUIRED — spec.md FR-027 and SC-009 mandate automated test coverage for authentication,
authorization, role protection, account status, and the specified security rules.

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent implementation and
testing of each story, in priority order (P1 stories first, then P2, then P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1, US2A, US2B, US2, US3, US4, US5, US6, US7, US8)
- Exact file paths are included in every task description

## Path Conventions

Single backend project (per plan.md): `src/` and `tests/` at repository root. No frontend is in scope for this
feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: `src/api/`, `src/application/`, `src/domain/`,
  `src/infrastructure/db/`, `src/infrastructure/security/`, `tests/contract/`, `tests/integration/`,
  `tests/unit/`, with an `__init__.py` in every Python package directory
- [X] T002 Initialize the Python 3.12 project in `pyproject.toml` with runtime dependencies: `fastapi`,
  `uvicorn[standard]`, `sqlalchemy>=2.0`, `alembic`, `argon2-cffi`, `pydantic>=2`, `python-dotenv`
- [X] T003 Add dev dependencies to `pyproject.toml`: `pytest`, `pytest-asyncio`, `httpx`, `ruff` (same file as
  T002 — run after it)
- [X] T004 Configure ruff linting/formatting under `[tool.ruff]` in `pyproject.toml` (same file as T002/T003 —
  run after them)
- [X] T005 Configure pytest under `[tool.pytest.ini_options]` in `pyproject.toml` (`asyncio_mode = "auto"`,
  `testpaths = ["tests"]`) (same file as T002–T004 — run after them)
- [X] T006 [P] Create `docker-compose.yml` with a local PostgreSQL service, and `.env.example` listing
  `DATABASE_URL`, `SESSION_DURATION_MINUTES`, `PASSWORD_RESET_LINK_DURATION_MINUTES`,
  `LOGIN_LOCKOUT_THRESHOLD`, `LOGIN_LOCKOUT_DURATION_MINUTES`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Define the `Role` enum in `src/domain/models.py` with exactly three values per data-model.md:
  "CITIZEN | OFFICER | ADMIN — exactly one value per UserAccount at any time"
- [X] T008 Define the `AccountStatus` enum in `src/domain/models.py` with exactly two values per data-model.md:
  "ACTIVE | DISABLED" (same file as T007 — run after it)
- [X] T009 Implement the environment-based settings loader in `src/infrastructure/config.py` reading
  `DATABASE_URL`, `SESSION_DURATION_MINUTES`, `PASSWORD_RESET_LINK_DURATION_MINUTES`,
  `LOGIN_LOCKOUT_THRESHOLD` (default 5), `LOGIN_LOCKOUT_DURATION_MINUTES` (default 15) (depends on T006)
- [X] T010 Set up the SQLAlchemy engine and session factory in `src/infrastructure/db/session.py` using
  `DATABASE_URL` from config (depends on T009)
- [X] T011 [P] Implement Argon2id password hashing/verification (`hash_password`, `verify_password`) in
  `src/infrastructure/security/hashing.py`
- [X] T012 [P] Implement opaque token generation/hashing (`generate_token`, `hash_token`) for session and
  reset-link tokens in `src/infrastructure/security/tokens.py`
- [X] T013 Create the `UserAccount` ORM model in `src/infrastructure/db/models.py` with fields per
  data-model.md: "id UUID (PK)", "email citext/case-insensitive text, UNIQUE, NOT NULL", "password_hash text,
  NOT NULL", "role enum(Role), NOT NULL, default CITIZEN", "status enum(AccountStatus), NOT NULL, default
  ACTIVE", "created_at timestamptz, NOT NULL", "updated_at timestamptz, NOT NULL" (depends on T007, T008, T010)
- [X] T014 Create the `Session` ORM model in `src/infrastructure/db/models.py` with fields per data-model.md:
  "id UUID (PK)", "user_id UUID (FK → UserAccount.id), NOT NULL", "token_hash text, UNIQUE, NOT NULL",
  "created_at timestamptz, NOT NULL", "expires_at timestamptz, NOT NULL", "revoked_at timestamptz, nullable"
  (same file as T013 — run after it)
- [X] T015 Create the `AuditRecord` ORM model in `src/infrastructure/db/models.py` with fields per
  data-model.md: "id UUID (PK)", "actor_user_id UUID (FK → UserAccount.id), nullable", "action text, NOT NULL"
  (one of REGISTER, LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, PASSWORD_RESET_REQUESTED, PASSWORD_RESET_COMPLETED,
  ACCOUNT_ENABLED, ACCOUNT_DISABLED, ROLE_CHANGED), "affected_user_id UUID (FK → UserAccount.id), NOT NULL",
  "occurred_at timestamptz, NOT NULL", "detail jsonb, nullable" (same file as T013/T014 — run after them).
  NOTE: PasswordResetRequest (T060) and LoginAttemptRecord (T070) were also created in this same file/migration
  now, for efficiency, instead of deferred to US5/US7 — their service-layer logic is still built in those phases.
- [X] T016 Initialize Alembic in `src/infrastructure/db/migrations/` and generate the initial migration creating
  the `user_accounts`, `sessions`, `audit_records`, `password_reset_requests`, and `login_attempt_records`
  tables (depends on T013, T014, T015); applied to both the dev and test PostgreSQL databases
- [X] T017 [P] Implement `AuditService.record_event()` in `src/application/audit_service.py`, writing an
  `AuditRecord` row; it MUST NOT accept or persist any password value (FR-026) (depends on T015)
- [X] T018 [P] Create a database seed script `scripts/seed_admin.py` that creates the system's first ACTIVE
  Admin account out-of-band — per spec Assumptions, the last-ACTIVE-Admin invariant means the API itself can
  never create the first Admin (depends on T013, T011)
- [X] T019 Implement the FastAPI app entrypoint in `src/main.py`, wiring DB session lifecycle and a generic
  exception handler whose error bodies never leak internal detail or secrets (depends on T010)
- [X] T020 Implement the `get_current_session`/`get_current_user` FastAPI dependency in
  `src/api/dependencies.py`: resolve the Bearer token, hash it, look up the `Session` by `token_hash`, and
  treat it as valid only if "revoked_at IS NULL AND now() < expires_at AND UserAccount.status = ACTIVE" per
  data-model.md's Session validity rule (depends on T014, T012)
- [X] T021 Implement the `require_role(*roles)` FastAPI dependency factory in `src/api/dependencies.py`
  wrapping `get_current_user`, returning 403 if the caller's role is not in the allowed set; define
  `require_admin = require_role(Role.ADMIN)` (same file as T020 — run after it; depends on T007). NOTE:
  `require_citizen`/`require_officer` (T046) were also defined here now for efficiency.

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Citizen Registration and First Login (Priority: P1) 🎯 MVP

**Goal**: A new resident can register (always as Citizen), log in, and view their own profile.

**Independent Test**: Register a new account, confirm it is created with the Citizen role, log in with the new
credentials, and reach `GET /users/me`.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T022 [P] [US1] Contract test for `POST /auth/register` in `tests/contract/test_auth_register.py`:
  201 response never includes a password field; created role is always `"citizen"` even if the request body
  supplies a different role; 409 on duplicate email; 422 on malformed email/password
- [X] T023 [P] [US1] Contract test for `POST /auth/login` in `tests/contract/test_auth_login.py`: 200 with
  `session_token` + `expires_at` on valid credentials; 401 with a generic `{"error":"invalid_credentials"}`
  body on wrong password
- [X] T024 [P] [US1] Contract test for `GET /users/me` in `tests/contract/test_users_me.py`: 200 with the
  caller's own id/email/role/status/created_at and no password field; 401 without a valid session
- [X] T025 [P] [US1] Integration test for the full register → login → view-own-profile flow in
  `tests/integration/test_registration_login_flow.py` (spec User Story 1, Acceptance Scenarios 1–3)
- [X] T026 [P] [US1] Integration test for duplicate-email registration rejection and client-supplied role being
  ignored in `tests/integration/test_registration_edge_cases.py` (spec User Story 1, Acceptance Scenario 4 and
  Edge Cases)

### Implementation for User Story 1

- [X] T027 [US1] Implement `AuthService.register()` in `src/application/auth_service.py`: hash the password
  (T011), create a `UserAccount` with role always `CITIZEN` and status `ACTIVE` regardless of any
  client-supplied role (FR-002, FR-003), enforce the unique-email constraint, and call
  `AuditService.record_event()` with action `REGISTER` (depends on T013, T011, T017)
- [X] T028 [US1] Implement `AuthService.login()` in `src/application/auth_service.py`: verify email + password
  via hashing (T011), verify `status == ACTIVE`, create a `Session` row with a generated opaque token (T012),
  and call `AuditService.record_event()` with action `LOGIN_SUCCESS` or `LOGIN_FAILURE` (same file as T027 —
  run after it; depends on T014, T011, T012, T017)
- [X] T029 [US1] Implement `POST /auth/register` endpoint in `src/api/auth.py` per contracts/auth-api.md,
  mapping `AuthService.register()` outcomes to 201/409/422 (depends on T027)
- [X] T030 [US1] Implement `POST /auth/login` endpoint in `src/api/auth.py` per contracts/auth-api.md, mapping
  `AuthService.login()` outcomes to 200/401 with the generic `invalid_credentials` body on any failure (same
  file as T029 — run after it; depends on T028)
- [X] T031 [P] [US1] Implement `GET /users/me` endpoint in `src/api/users.py` using the `get_current_user`
  dependency (T020), returning only the caller's own id/email/role/status/created_at fields (no
  `password_hash`) (depends on T020, T013)
- [X] T032 [US1] Register the `auth` and `users` routers on the FastAPI app in `src/main.py` (depends on T029,
  T030, T031)

**Checkpoint**: User Story 1 is fully functional and independently testable

---

## Phase 4: User Story 2a - Admin Role Assignment (Priority: P1)

**Goal**: An Admin can promote a Citizen/Officer to Officer/Admin, since no one can self-assign those roles.

**Independent Test**: As the seeded Admin, change another user's role and confirm it takes effect on their next
authorization check.

### Tests for User Story 2a ⚠️

- [X] T033 [P] [US2A] Contract test for `PATCH /admin/users/{user_id}/role` in `tests/contract/test_admin_role.py`:
  200 for a valid Admin-issued change; 403 for a non-Admin caller; 403 for an Admin targeting their own account
  away from admin; 409 when the change would remove the last ACTIVE Admin; 422 for a role value outside
  citizen/officer/admin
- [X] T034 [P] [US2A] Integration test: Admin promotes a Citizen to Officer then to Admin, the target's enforced
  role changes on its next authorization check, and a `ROLE_CHANGED` audit record is created, in
  `tests/integration/test_admin_role_assignment.py` (spec User Story 2a, Acceptance Scenarios 1 and 3)
- [X] T035 [P] [US2A] Integration test: non-Admin role-change attempts are denied, Admin self-demotion away from
  Admin is denied, and a role change that would leave zero ACTIVE Admins is denied, in
  `tests/integration/test_admin_role_invariants.py` (spec User Story 2a, Acceptance Scenarios 2, 4, 5; FR-004d,
  FR-004e)

### Implementation for User Story 2a

- [X] T036 [US2A] Implement `RoleService.change_role()` in `src/application/role_service.py` enforcing: only
  CITIZEN/OFFICER/ADMIN are valid target values (FR-004c); reject if the acting Admin targets their own
  account with a non-ADMIN value (FR-004d); reject if applying the change would make
  "COUNT(UserAccount WHERE role = ADMIN AND status = ACTIVE) >= 1" false per data-model.md's cross-entity
  invariant (FR-004e); call `AuditService.record_event()` with action `ROLE_CHANGED` on success (depends on
  T013, T017, T007)
- [X] T037 [US2A] Implement `PATCH /admin/users/{user_id}/role` endpoint in `src/api/admin.py` using the
  `require_admin` dependency (T021), mapping `RoleService.change_role()` outcomes to 200/403/409/422 per
  contracts/auth-api.md (depends on T036, T021)
- [X] T038 [US2A] Register the `admin` router on the FastAPI app in `src/main.py` (depends on T037)

**Checkpoint**: User Story 2a is fully functional and independently testable (requires the seed Admin from T018)

---

## Phase 5: User Story 2b - Admin Account Status Management (Priority: P2)

**Goal**: An Admin can enable/disable any account except their own, and the system never reaches zero ACTIVE
Admins.

**Independent Test**: As Admin, disable/enable another account; confirm non-Admins, self-targeting, and
last-admin removal are all denied.

### Tests for User Story 2b ⚠️

- [X] T039 [P] [US2B] Contract test for `PATCH /admin/users/{user_id}/status` in
  `tests/contract/test_admin_status.py`: 200 for a valid Admin-issued change; 403 for a non-Admin caller; 403
  when the caller targets their own account; 409 when disabling would remove the last ACTIVE Admin; 422 for a
  status value outside active/disabled
- [X] T040 [P] [US2B] Integration test: Admin disables then re-enables another account with an
  `ACCOUNT_DISABLED`/`ACCOUNT_ENABLED` audit record created each time, and the disabled account's existing
  session is immediately rejected, in `tests/integration/test_admin_status_management.py` (spec User Story 2b,
  Acceptance Scenario 1; FR-021)
- [X] T041 [P] [US2B] Integration test: non-Admin status-change attempts are denied, self-disable attempts are
  denied for any role including Admin, and a disable that would leave zero ACTIVE Admins is denied, in
  `tests/integration/test_admin_status_invariants.py` (spec User Story 2b, Acceptance Scenarios 2, 3, 4)

### Implementation for User Story 2b

- [X] T042 [US2B] Implement `AccountStatusService.change_status()` in
  `src/application/account_status_service.py` enforcing: reject if the caller targets their own account
  (FR-019c); reject if disabling would make "COUNT(UserAccount WHERE role = ADMIN AND status = ACTIVE) >= 1"
  false (FR-019d); on transition to DISABLED, revoke every active `Session` for that user (set
  `revoked_at = now()` where `user_id` matches and `revoked_at IS NULL`) per FR-021; call
  `AuditService.record_event()` with action `ACCOUNT_ENABLED` or `ACCOUNT_DISABLED` on success (depends on
  T013, T014, T017)
- [X] T043 [US2B] Implement `PATCH /admin/users/{user_id}/status` endpoint in `src/api/admin.py` using the
  `require_admin` dependency (T021), mapping `AccountStatusService.change_status()` outcomes to
  200/403/409/422 per contracts/auth-api.md (same file as T037 — run after it; depends on T042, T021)

**Checkpoint**: User Story 2b is fully functional and independently testable

---

## Phase 6: User Story 2 - Role-Based Access Enforcement (Priority: P1)

**Goal**: Citizens, Officers, and Admins each reach only their own role's functionality; the backend enforces
this identically for every caller.

**Independent Test**: Authenticate as each role and call citizen-only, officer-only, and admin-only operations;
confirm only permitted calls succeed.

**Note**: This feature is auth/RBAC plumbing only — LocalFix's actual citizen/officer business functionality is
out of this feature's scope (see spec Assumptions). This phase adds minimal demonstration endpoints solely to
prove and test the generic role-gating mechanism; admin-only enforcement is already proven by US2a/US2b.

### Tests for User Story 2 ⚠️

- [X] T044 [P] [US2] Contract test for the demonstration role-protected endpoints in
  `tests/contract/test_role_protected_endpoints.py`: `GET /citizen/ping` returns 200 only for role citizen;
  `GET /officer/ping` returns 200 only for role officer; both return 403 for every other role
- [X] T045 [P] [US2] Integration test: a Citizen is denied `GET /officer/ping` and the admin-only endpoints from
  US2a/US2b; an Officer succeeds at `GET /officer/ping` but is denied the admin-only endpoints; an Admin
  succeeds at the admin-only endpoints; a direct HTTP call bypassing any client-side logic is enforced
  identically, in `tests/integration/test_role_enforcement.py` (spec User Story 2, Acceptance Scenarios 1–5)

### Implementation for User Story 2

- [X] T046 [US2] Add `require_citizen = require_role(Role.CITIZEN)` and
  `require_officer = require_role(Role.OFFICER)` in `src/api/dependencies.py`, reusing the `require_role`
  factory from T021 (same file as T020/T021 — run after them)
- [X] T047 [US2] Implement demonstration-only `GET /citizen/ping` (using `require_citizen`) in
  `src/api/citizen.py` and `GET /officer/ping` (using `require_officer`) in `src/api/officer.py`, solely to
  prove/verify the role-gating mechanism per FR-012/FR-013; register both routers in `src/main.py` (depends on
  T046)

**Checkpoint**: User Story 2 is fully functional and independently testable

---

## Phase 7: User Story 3 - Protecting Other Users' Information (Priority: P1)

**Goal**: No user can view or modify another user's protected information through any exposed endpoint.

**Independent Test**: As User A, attempt to retrieve/modify User B's data by any identifier; confirm every
attempt is denied.

### Tests for User Story 3 ⚠️

- [X] T048 [P] [US3] Integration test: an authenticated User A cannot retrieve or modify User B's profile or
  account data through any endpoint or parameter, including guessed/incremented identifiers, in
  `tests/integration/test_cross_user_protection.py` (spec User Story 3, Acceptance Scenarios 1–3)

### Implementation for User Story 3

- [X] T049 [P] [US3] Audit every non-admin route in `src/api/users.py`, `src/api/citizen.py`, and
  `src/api/officer.py` to confirm none accepts a client-supplied target-user identifier — each resolves its
  subject solely from the validated session (`get_current_user`, T020) (depends on T031, T047)
- [X] T050 [P] [US3] Audit the admin-only endpoints in `src/api/admin.py` to confirm a target `user_id` is only
  ever reachable under the `require_admin` dependency (T021), and that no non-admin caller can be routed to
  another user's data (depends on T037, T043)

**Checkpoint**: User Story 3 is fully functional and independently testable (primarily a verification/regression
story, since the contract already scopes all non-admin reads to the caller)

---

## Phase 8: User Story 4 - Logout and Session Expiration (Priority: P2)

**Goal**: A user can end their session on demand; any unterminated session stops working once expired.

**Independent Test**: Log in, log out, confirm the prior session is rejected; separately confirm an expired
session is rejected.

### Tests for User Story 4 ⚠️

- [X] T051 [P] [US4] Contract test for `POST /auth/logout` in `tests/contract/test_auth_logout.py`: 204 on
  success, and the same `session_token` subsequently fails on any protected endpoint with 401
- [X] T052 [P] [US4] Integration test: login → logout → the prior `session_token` is rejected on
  `GET /users/me`, in `tests/integration/test_logout_flow.py` (spec User Story 4, Acceptance Scenario 1)
- [X] T053 [P] [US4] Integration test: a session whose `expires_at` has passed is rejected on `GET /users/me`
  even though it was never explicitly logged out, using a test-only short session duration, in
  `tests/integration/test_session_expiration.py` (spec User Story 4, Acceptance Scenario 2)

### Implementation for User Story 4

- [X] T054 [US4] Implement `AuthService.logout()` in `src/application/auth_service.py`: set
  `revoked_at = now()` on the `Session` matching the presented token, and call `AuditService.record_event()`
  with action `LOGOUT` (depends on T014, T017, T028)
- [X] T055 [US4] Implement `POST /auth/logout` endpoint in `src/api/auth.py` using the `get_current_user`
  dependency (T020), calling `AuthService.logout()` and returning 204 (depends on T054, T020)

**Checkpoint**: User Story 4 is fully functional and independently testable

---

## Phase 9: User Story 5 - Password Reset (Priority: P2)

**Goal**: A user who forgot their password can self-service reset it via a single-use, time-limited emailed
link.

**Independent Test**: Request a reset, complete it via the issued token, confirm login works with the new
password and fails with the old one.

### Tests for User Story 5 ⚠️

- [X] T056 [P] [US5] Contract test for `POST /auth/password-reset/request` in
  `tests/contract/test_password_reset_request.py`: identical 202 response body for both a registered and an
  unregistered email, with no email sent for the unregistered case
- [X] T057 [P] [US5] Contract test for `POST /auth/password-reset/confirm` in
  `tests/contract/test_password_reset_confirm.py`: 200 on a valid, unexpired, unused token; 400 on an invalid,
  expired, or already-used token
- [X] T058 [P] [US5] Integration test: request reset → confirm with the issued token → new password logs in
  successfully → old password is rejected, in `tests/integration/test_password_reset_flow.py` (spec User
  Story 5, Acceptance Scenarios 1–3)
- [X] T059 [P] [US5] Integration test: requesting reset for an unregistered email creates no
  `PasswordResetRequest` row and sends no email; reusing an already-confirmed token is rejected; issuing a
  second reset request invalidates the first, in `tests/integration/test_password_reset_edge_cases.py` (spec
  User Story 5, Acceptance Scenarios 4–5; FR-010a, FR-010b)

### Implementation for User Story 5

- [X] T060 [US5] Create the `PasswordResetRequest` ORM model in `src/infrastructure/db/models.py` with fields
  per data-model.md: "id UUID (PK)", "user_id UUID (FK → UserAccount.id), NOT NULL", "token_hash text, UNIQUE,
  NOT NULL", "created_at timestamptz, NOT NULL", "expires_at timestamptz, NOT NULL", "used_at timestamptz,
  nullable"; add an Alembic migration for the new table (depends on T013, T016)
- [X] T061 [US5] Implement `PasswordResetService.request_reset()` in
  `src/application/password_reset_service.py`: if the email matches a `UserAccount`, invalidate any prior
  unused `PasswordResetRequest` for that user, create a new one with a generated token (T012), and send the
  reset email; if it does not match, do nothing observable (FR-010b); call `AuditService.record_event()` with
  action `PASSWORD_RESET_REQUESTED` only when a request was actually created (depends on T060, T012, T017)
- [X] T062 [US5] Implement `PasswordResetService.confirm_reset()` in
  `src/application/password_reset_service.py`: validate the token against an unused, unexpired
  `PasswordResetRequest` per data-model.md's validity rule "used_at IS NULL AND now() < expires_at"; update the
  `UserAccount.password_hash` via hashing (T011); set `used_at = now()`; call
  `AuditService.record_event()` with action `PASSWORD_RESET_COMPLETED` (same file as T061 — run after it;
  depends on T060, T011, T017)
- [X] T063 [US5] Implement `POST /auth/password-reset/request` and `POST /auth/password-reset/confirm`
  endpoints in `src/api/auth.py` per contracts/auth-api.md (depends on T061, T062)

**Checkpoint**: User Story 5 is fully functional and independently testable

---

## Phase 10: User Story 6 - Account Disablement Enforcement (Priority: P2)

**Goal**: A DISABLED account cannot authenticate or keep using an existing session, even with correct
credentials.

**Independent Test**: Disable an account and confirm correct-credential login and any existing session are
both rejected.

### Tests for User Story 6 ⚠️

- [X] T064 [P] [US6] Integration test: a DISABLED account's login attempt with fully correct credentials is
  denied with the same generic `invalid_credentials` response as a wrong password, in
  `tests/integration/test_disabled_account_login.py` (spec User Story 6, Acceptance Scenario 1; FR-020)
- [X] T065 [P] [US6] Integration test: an account's existing session is rejected immediately after that account
  transitions to DISABLED while the session was still otherwise valid, in
  `tests/integration/test_disabled_account_session.py` (spec User Story 6, Acceptance Scenario 2; FR-021)

### Implementation for User Story 6

- [X] T066 [US6] Extend `AuthService.login()` in `src/application/auth_service.py` to deny authentication when
  `UserAccount.status != ACTIVE`, returning the same generic failure as a wrong password without disclosing
  which condition failed (FR-020) (depends on T028)
- [X] T067 [P] [US6] Confirm `get_current_user` (T020) in `src/api/dependencies.py` already rejects any session
  whose owning `UserAccount.status != ACTIVE` per the Session validity rule, adding the check if it is missing
  (depends on T020, T042)

**Checkpoint**: User Story 6 is fully functional and independently testable

---

## Phase 11: User Story 7 - Brute-Force Login Protection (Priority: P2)

**Goal**: Repeated failed logins against an account are throttled so password guessing is impractical.

**Independent Test**: Submit 5 consecutive failed logins against one account and confirm further attempts
(even correct ones) are blocked until the cool-down elapses.

### Tests for User Story 7 ⚠️

- [X] T068 [P] [US7] Contract test: 5 consecutive failed logins against one account lock it out, and a
  subsequent attempt with the correct password within the cool-down still returns 401, in
  `tests/contract/test_login_lockout.py`
- [X] T069 [P] [US7] Integration test: full lockout → cool-down-elapsed → successful login flow, confirming the
  failure counter resets to zero on success, in `tests/integration/test_brute_force_lockout.py` (spec User
  Story 7, Acceptance Scenarios 1–3)

### Implementation for User Story 7

- [X] T070 [US7] Create the `LoginAttemptRecord` ORM model in `src/infrastructure/db/models.py` with fields per
  data-model.md: "user_id UUID (PK, FK → UserAccount.id)", "consecutive_failures integer, NOT NULL, default
  0", "locked_until timestamptz, nullable"; add an Alembic migration for the new table (depends on T013, T016)
- [X] T071 [US7] Extend `AuthService.login()` in `src/application/auth_service.py` to: reject outright while
  "locked_until IS NOT NULL AND now() < locked_until" per data-model.md's validity rule (FR-022); otherwise, on
  failed credentials, increment `consecutive_failures` and set `locked_until` once it reaches
  `LOGIN_LOCKOUT_THRESHOLD` (default 5) for `LOGIN_LOCKOUT_DURATION_MINUTES` (default 15); on success, reset
  `consecutive_failures` to 0 (FR-022a) (depends on T070, T028, T009)

**Checkpoint**: User Story 7 is fully functional and independently testable

---

## Phase 12: User Story 8 - Security Audit Trail (Priority: P3)

**Goal**: Security-sensitive authentication/account actions are recorded and reviewable after the fact.

**Independent Test**: Perform register/login/logout/reset/role-change/enable-disable actions and confirm each
produces a matching, retrievable audit record with no secret values.

### Tests for User Story 8 ⚠️

- [X] T072 [P] [US8] Contract test for `GET /admin/audit-log` in `tests/contract/test_admin_audit_log.py`: 200
  with an `items` array whose entries never include any password value; 403 for non-Admin callers
- [X] T073 [P] [US8] Integration test: after performing registration, login success/failure, logout, password
  reset, role change, and account enable/disable, `GET /admin/audit-log` contains a matching entry for each
  with a non-null actor/affected-user/action/occurred_at, in
  `tests/integration/test_audit_trail_completeness.py` (spec User Story 8, Acceptance Scenarios 1–2; FR-024,
  FR-025, FR-026)

### Implementation for User Story 8

- [X] T074 [US8] Implement `GET /admin/audit-log` endpoint in `src/api/admin.py` using the `require_admin`
  dependency (T021), returning `AuditRecord` entries per contracts/auth-api.md with optional filters (depends
  on T021, T015)

**Checkpoint**: All user stories are now independently functional

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T075 [P] Run the quickstart.md validation scenarios end-to-end against a running instance and record
  results
- [X] T076 [P] Add unit tests for `AuthService`/`RoleService`/`AccountStatusService`/`PasswordResetService`
  pure-logic branches (no DB) in `tests/unit/`
- [X] T077 [P] Review all log statements across `src/` to confirm no password, token, or `password_hash` value
  is ever logged (FR-018, FR-026)
- [X] T078 [P] Review all API response schemas across `src/api/` to confirm no endpoint can serialize
  `password_hash` (FR-017)
- [X] T079 [P] Add `README.md` documenting setup, running migrations, seeding the first Admin (T018), and
  running the test suites

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–12)**: All depend on Foundational completion; proceed in priority order
  (P1 → P2 → P3) or in parallel if staffed, respecting the intra-story notes below
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories — true MVP
- **US2A (P1)**: Independent of US1 at the data layer, but needs a seeded Admin (T018, Foundational) to exercise
- **US2B (P2)**: Builds on US2A's `admin.py` router file and the Session model; independently testable once
  Foundational + an Admin exist
- **US2 (P1)**: Independent; demonstration endpoints only depend on Foundational dependencies
- **US3 (P1)**: Verification-only story; depends on US1 (`users.py`), US2 (`citizen.py`/`officer.py`), US2A/US2B
  (`admin.py`) already existing to audit
- **US4 (P2)**: Extends `AuthService` from US1 (adds `logout()`)
- **US5 (P2)**: Independent new service/table; only needs Foundational
- **US6 (P2)**: Extends `AuthService.login()` from US1 and `get_current_user` from Foundational; also
  references US2B's disable capability for its test setup
- **US7 (P2)**: Extends `AuthService.login()` from US1/US6
- **US8 (P3)**: Depends on audit events already being written by every prior story to have something to
  display

### Within Each User Story

- Tests MUST be written first and FAIL before implementation
- Models before services; services before endpoints; endpoints before router registration
- Story complete and checkpointed before moving to the next priority tier

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel with each other (T006 only — T002–T005 share `pyproject.toml`)
- Foundational [P] tasks (T011, T012, T017, T018) can run in parallel once their individual dependencies are met
- Once Foundational completes, independent stories (US1, US2A, US2, US5) can be staffed in parallel; US2B, US3,
  US4, US6, US7, US8 should follow once their prerequisite stories' files exist
- All test tasks within a story marked [P] can run in parallel with each other

---

## Phase 14: Convergence

**Purpose**: Close gaps found by `/speckit-converge` between spec.md/plan.md/tasks.md and the current
codebase, after `/speckit-implement` completed all tasks through Phase 13.

- [X] T080 Add a `.gitignore` excluding `.env`, `.venv/`, `.pgdata/`, `__pycache__/`, `*.pyc`,
  `.pytest_cache/`, and `.ruff_cache/` per Constitution: Security and Privacy (missing)
- [X] T081 Implement the `user_id`/`action`/date-range query filters on `GET /admin/audit-log` in
  `src/api/admin.py` that it is documented as supporting per contracts/auth-api.md: GET /admin/audit-log
  (partial)
- [X] T082 Update `contracts/auth-api.md` to document the `GET /citizen/ping` and `GET /officer/ping`
  demonstration endpoints and the `404 user_not_found` response already returned by both
  `PATCH /admin/users/{user_id}/role` and `PATCH /admin/users/{user_id}/status` per tasks.md: T047
  (partial)

---

## Phase 15: Security Hardening

**Purpose**: Close findings F1–F8, F10, F11 from the 2026-10-07 post-implementation security review,
per spec.md FR-028–FR-031/SC-013–SC-016 and plan.md's Security Hardening Addendum. F9 (CORS), F12
(Argon2 cost tuning), and F13 (structured logging/health endpoint) are **explicitly deferred** — see
"Deferred Findings" at the end of this phase; no tasks exist for them here.

**Decisions already made** (not open for `/speckit-clarify` — see spec.md Clarifications, Session
2026-10-07): password length 8–128 chars, no forced complexity (F2/F3); rate limiting 5 req/15min per
source IP, PostgreSQL-backed, no new infrastructure (F7); API docs disabled only when
`environment=production` (F6).

### F1 — Login timing side-channel (HIGH)

- [X] T083 [P] Add a test proving the nonexistent-email login path invokes password verification
  against a fixed dummy hash (not a short-circuit), so its cost matches the wrong-password path, in
  `tests/unit/test_login_timing_safety.py` per FR-031 (F1)
- [X] T084 In `src/application/auth_service.py::login()`, call `verify_password()` against a fixed
  dummy Argon2 hash whenever the account doesn't exist, so both branches always pay the same hashing
  cost per FR-031 (F1)

### F2 + F3 — Password length policy (MEDIUM)

- [X] T085 [P] Add boundary contract tests for `POST /auth/register` and
  `POST /auth/password-reset/confirm`: 7 chars → 422, 8 chars → accepted, 128 chars → accepted, 129
  chars → 422, in `tests/contract/test_password_policy.py` per FR-028/SC-013 (F2, F3)
- [X] T086 Add `min_length=8, max_length=128` to the `password` field in `RegisterRequest` and the
  `new_password` field in `PasswordResetConfirmBody` in `src/api/schemas.py`; no complexity rules per
  FR-028 (F2, F3)

### F4 — Email case-insensitivity (MEDIUM)

- [X] T087 [P] Add an integration test: registering `Alice@Example.com` then
  `alice@example.com` is rejected as a duplicate (409); logging in with either casing of an already
  registered email succeeds, in `tests/integration/test_email_case_insensitivity.py` per
  FR-029/SC-015 (F4)
- [X] T088 Normalize email to lowercase (e.g. `email.strip().lower()`) before every query/insert in
  `src/application/auth_service.py` (`register`, `login`) and
  `src/application/password_reset_service.py` (`request_reset`) per FR-029 (F4)
- [X] T089 Add an Alembic migration adding a unique index on `lower(email)` on `user_accounts` in
  `src/infrastructure/db/migrations/versions/`, as DB-layer defense-in-depth beyond the T088
  application-layer normalization per FR-029 (F4) **[DB MIGRATION]**

### F5 — Last-admin TOCTOU race (MEDIUM)

- [X] T090 [P] Add an integration test that opens two separate DB sessions/transactions and
  deterministically interleaves them (read both counts before either commits) to reproduce the race
  window, asserting the second commit is rejected rather than silently succeeding, in
  `tests/integration/test_last_admin_race.py` per FR-004e/FR-019d (F5)
- [X] T091 Add `.with_for_update()` row locking to the active-admin-count query
  (`_active_admin_count`) in `src/application/role_service.py` and
  `src/application/account_status_service.py`, so concurrent last-admin checks serialize correctly
  per FR-004e/FR-019d (F5)

### F6 + F10 — Environment-aware configuration (MEDIUM / LOW)

- [X] T092 [P] Add a unit test asserting `Settings()` raises a clear startup error when
  `DATABASE_URL` is unset, instead of silently falling back to a dev default, in
  `tests/unit/test_config_fail_fast.py` (F10)
- [X] T093 In `src/infrastructure/config.py`: add `environment: Literal["development", "production"] =
  "development"`; remove the hardcoded default for `database_url` (make it a required field with no
  fallback) (F6, F10)
- [X] T094 [P] Add a contract test asserting `GET /docs`, `GET /redoc`, and `GET /openapi.json` return
  `404` when `environment=production`, and remain available (`200`) when `environment=development`,
  in `tests/contract/test_docs_exposure.py` (F6)
- [X] T095 In `src/main.py`, conditionally pass `docs_url=None, redoc_url=None, openapi_url=None` to
  `FastAPI(...)` when `settings.environment == "production"` (F6)

### F7 — Rate limiting (MEDIUM)

- [X] T096 [P] Add contract tests asserting the 6th request within 15 minutes from one source IP to
  `POST /auth/register` and to `POST /auth/password-reset/request` returns `429`, and that a
  different source IP is unaffected, in `tests/contract/test_registration_rate_limit.py` and
  `tests/contract/test_reset_request_rate_limit.py` per FR-030/SC-014 (F7)
- [X] T097 Create a `RateLimitRecord` ORM model (`source_ip`, `endpoint`, `window_start`,
  `request_count`) in `src/infrastructure/db/models.py`, mirroring the existing
  `LoginAttemptRecord` pattern; add an Alembic migration for the new table per FR-030 (F7)
  **[DB MIGRATION]**
- [X] T098 Implement `src/application/rate_limit_service.py` enforcing 5 requests per 15 minutes per
  `source_ip` + `endpoint`; wire it as a FastAPI dependency on `POST /auth/register` and
  `POST /auth/password-reset/request` in `src/api/auth.py` per FR-030 (F7)

### F8 — Error response consistency (LOW)

- [X] T099 [P] Add a contract test asserting a `422` response (e.g., malformed email on
  `/auth/register`) returns the same `{"error": "..."}` shape as every other error response, in
  `tests/contract/test_validation_error_shape.py` (F8)
- [X] T100 Register a custom `RequestValidationError` exception handler in `src/main.py` mapping
  Pydantic validation errors to `{"error": "validation_error"}`; update `contracts/auth-api.md`'s
  Cross-cutting rules to document the unified 422 shape (F8)

### F11 — Argon2 exception robustness (INFORMATIONAL)

- [X] T101 [P] Add a unit test asserting `verify_password()` returns `False` (not an unhandled
  exception) when given a malformed/non-Argon2 `password_hash` string, in
  `tests/unit/test_hashing.py` (F11)
- [X] T102 Widen the caught exception in `src/infrastructure/security/hashing.py::verify_password`
  from `argon2.exceptions.VerifyMismatchError` to its base class
  `argon2.exceptions.VerificationError` (F11)

**Checkpoint**: All HIGH/MEDIUM/LOW findings from the 2026-10-07 security review are closed; the full
suite (existing 64 tests + ~20 new tests from T083–T102) passes before this phase is considered done.

**Deferred Findings** (explicitly out of scope for this phase — no tasks created; see spec.md
Assumptions and plan.md's Security Hardening Addendum for rationale):

- **F9** (INFORMATIONAL) — No CORS policy configured. Deferred until a frontend consumer exists to
  design the policy against; the current absence fails closed (safe), so there is nothing to fix yet.
- **F12** (INFORMATIONAL) — Argon2 cost parameters are library defaults, unreviewed for this
  deployment. Deferred until real deployment/capacity data is available to tune against.
- **F13** (INFORMATIONAL) — No structured application logging or health-check endpoint. Deferred as a
  separate, future observability feature rather than scope-creep into Feature 001.

---

## Phase 16: Convergence

**Purpose**: Close gaps found by `/speckit-converge` between spec.md/plan.md/tasks.md and the current
codebase, after `/speckit-implement` completed Phase 15 (Security Hardening).

- [X] T103 Add a test simulating the rate-limit window elapsing (direct manipulation of
  `RateLimitRecord.window_start`, mirroring the pattern already used in
  `tests/integration/test_brute_force_lockout.py` for lockout cooldown) and confirm a
  previously-blocked source IP can make requests again afterward, in
  `tests/integration/test_rate_limit_window_reset.py` per FR-030 (missing)
- [X] T104 Correct plan.md's Security Hardening Addendum F11 row to state that
  `verify_password` catches both `argon2.exceptions.VerificationError` and
  `argon2.exceptions.InvalidHashError` (not `VerificationError` alone), since argon2-cffi gives
  malformed-hash errors no common base class with verification-failure errors, per
  plan: Security Hardening Addendum F11 (partial)
- [X] T105 Add manual validation scenarios for FR-028 (password length bounds), FR-029
  (case-insensitive email), FR-030 (rate limiting), and FR-031 (login-timing safety) to
  quickstart.md, consistent with its existing per-user-story scenario format, per
  plan: quickstart.md (partial)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /auth/register in tests/contract/test_auth_register.py"
Task: "Contract test for POST /auth/login in tests/contract/test_auth_login.py"
Task: "Contract test for GET /users/me in tests/contract/test_users_me.py"
Task: "Integration test for registration+login+profile flow in tests/integration/test_registration_login_flow.py"
Task: "Integration test for duplicate-email/role-ignore edge cases in tests/integration/test_registration_edge_cases.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (register → login → view profile)
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test independently → MVP
3. US2A → test independently (role assignment now possible)
4. US2B → test independently (account status control now possible)
5. US2 → test independently (generic role-gating proven)
6. US3 → test independently (cross-user protection verified)
7. US4 → test independently (logout/expiration)
8. US5 → test independently (password reset)
9. US6 → test independently (disablement enforcement, builds on US2B)
10. US7 → test independently (brute-force lockout)
11. US8 → test independently (audit trail, last — depends on everything else writing events)
12. Phase 13: Polish

### Parallel Team Strategy

With multiple developers, after Foundational:

- Developer A: US1 → US4 → US6 → US7 (the `AuthService`/login lineage)
- Developer B: US2A → US2B (the admin/role/status lineage)
- Developer C: US2 → US3 (role-gating + cross-user verification)
- Developer D: US5 (password reset, fully independent)
- US8 last, once the others are writing audit events

---

## Notes

- [P] tasks touch different files and have no incomplete-task dependency between them
- [Story] label maps each task to its spec.md user story for traceability
- Verify each test fails before implementing against it
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts marked [P], cross-story dependencies that break independent testability
