---

description: "Task list for Feature 002: LocalFix Frontend and Web Authentication"
---

# Tasks: LocalFix Frontend and Web Authentication

**Input**: Design documents from `/specs/002-web-frontend-auth/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/frontend-auth-api.md, quickstart.md (all present)

**Tests**: Included and REQUIRED per user instruction and spec SC-001–SC-010's testability requirements.

**Organization**: Tasks are grouped by user story (from spec.md), in priority order (P1 → P2 → P3). Every task is
explicitly labeled **(backend)** or **(frontend)** in its description in addition to the file path, per the
instruction to clearly separate the two.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US11, mapping to spec.md's user stories
- Setup/Foundational/Polish tasks carry no `[Story]` label, per convention

## Path Conventions

Two trees, side by side (per plan.md's Structure Decision): the existing backend at `src/`/`tests/` (extended in
place) and a new `frontend/` tree.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 (frontend) Create the Vite + React + TypeScript project scaffold: `frontend/package.json`,
  `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, per plan.md
  Project Structure
- [X] T002 (frontend) Add `react-router-dom` and `@tanstack/react-query` to `frontend/package.json` (same file
  as T001 — run after it)
- [X] T003 (frontend) Add Tailwind CSS to `frontend/package.json` and create `frontend/tailwind.config.js`,
  `frontend/postcss.config.js`, `frontend/src/index.css` (same `package.json` as T002 — run after it)
- [X] T004 (frontend) Add Vitest + React Testing Library to `frontend/package.json` and create
  `frontend/vitest.config.ts`, per research.md's frontend test-tooling decision (same `package.json` as T003 —
  run after it)
- [X] T005 [P] (frontend) Configure the Vite dev-server proxy in `frontend/vite.config.ts`, forwarding `/api/*`
  to the backend, per plan.md's same-origin development architecture (depends on T001; different file from
  T002–T004)
- [X] T006 [P] (backend) Add the new required environment variables to `.env.example`: `COOKIE_SECURE`,
  `TRUSTED_PROXY_IPS`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`, per
  data-model.md's New Configuration section

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 (backend) Add `cookie_secure: bool` (no default) to `Settings` in `src/infrastructure/config.py`,
  plus a model validator that raises at construction time when `environment == "production"` and
  `cookie_secure is False`, per spec BE-012/BE-013
- [X] T008 (backend) Add `trusted_proxy_ips: list[str] = []` to the same `Settings` class in
  `src/infrastructure/config.py` (same file as T007 — run after it), per spec BE-014/BE-015
- [X] T009 (backend) Add `smtp_host: str`, `smtp_port: int`, `smtp_username: str`, `smtp_password: str`,
  `smtp_from_address: str` (all required, no defaults) to the same `Settings` class in
  `src/infrastructure/config.py` (same file as T007/T008 — run after them), per spec BE-010
- [X] T010 [P] (backend) Implement `src/infrastructure/security/trusted_proxy.py`: an ASGI middleware that, only
  when the immediately connecting peer's address is in `settings.trusted_proxy_ips`, parses `X-Forwarded-For` by
  splitting on commas, trims whitespace, and rewrites `scope["client"]` using the **rightmost** value (never the
  whole header string as one IP); when the peer is not trusted, `scope["client"]` is left untouched, per
  research.md's trusted-proxy decision (depends on T008)
- [X] T011 (backend) Wire the trusted-proxy middleware into `src/main.py`, added before routing (depends on T010)
- [X] T012 [P] (backend) Implement `src/application/csrf_service.py`: `generate_csrf_token() -> str` and
  `verify_csrf_token(cookie_value, header_value) -> bool`, with no server-side storage, per data-model.md's CSRF
  token section
- [X] T013 (backend) Extend `get_current_user` in `src/api/dependencies.py` to fall back to a `session_id`
  cookie when no `Authorization` header is present, checking the header first, per spec BE-003
- [X] T014 (backend) Add a `require_csrf` FastAPI dependency in `src/api/dependencies.py` (same file as T013 —
  run after it) enforcing a matching `X-CSRF-Token` header against the `csrf_token` cookie, active only when
  `get_current_user` resolved the request via the cookie rather than the bearer header, per spec
  BE-006/BE-007/SEC-004 (depends on T012, T013)
- [X] T015 [P] (backend) Add the `WebSessionResponse` schema (`{expires_at: datetime}`, no token field) to
  `src/api/schemas.py`, per data-model.md
- [X] T016 (backend) Add `UserListItem`, `UserListResponse`, and query-parameter validation (`role`/`status`
  enums, `page >= 1`, `1 <= page_size <= 100`) to `src/api/schemas.py` (same file as T015 — run after it), per
  data-model.md and research.md's pagination defaults
- [X] T017 [P] (frontend) Implement the typed API client in `frontend/src/api/client.ts`: a fetch wrapper using
  `credentials: "include"`, automatic `X-CSRF-Token` header injection (read from the `csrf_token` cookie) on
  mutating requests, and centralized handling for `401` (clear auth state, redirect to login), `403` (surface a
  "not permitted" result), and `429` (surface a "too many attempts" result), per spec FE-018/FE-019/FE-020
- [X] T018 [P] (frontend) Implement the auth-context layer in `frontend/src/auth/AuthContext.tsx`, holding only
  `{currentUser, isAuthenticated}` — never a raw token — populated via `GET /users/me` at app load, per spec
  SEC-001
- [X] T019 [P] (frontend) Set up React Router in `frontend/src/routes/index.tsx` with route definitions for
  every in-scope page and role-aware route guards (redirect-only UX convenience, not enforcement), per spec
  FE-009/SEC-003
- [X] T020 [P] (frontend) Implement shared `LoadingState`, `ErrorState`, and `EmptyState` UI primitives in
  `frontend/src/components/`, per spec FE-015
- [X] T021 [P] (frontend) Implement the shared app-shell/navigation component in
  `frontend/src/components/AppShell.tsx` that adapts visible links to `currentUser.role`, per spec FE-009
- [X] T022 (frontend) Configure TanStack Query's `QueryClientProvider` at the app root in
  `frontend/src/main.tsx` (same file as T001 — run after it)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Register and Log In via the Web Frontend (Priority: P1) 🎯 MVP

**Goal**: A resident can register and log in through the web UI; the browser session is cookie-based and never
exposes the raw credential to frontend JS; existing bearer-token API clients are completely unaffected.

**Independent Test**: Register and log in through the web UI, confirm a protected page loads using only the
cookie; separately, confirm an existing bearer-token client still works unchanged.

### Tests for User Story 1 ⚠️

- [X] T023 [P] [US1] (backend) Contract test for `POST /auth/session`: success sets both cookies and returns
  `{expires_at}` with no `session_token` field; wrong credentials return the same generic `401` as
  `POST /auth/login`, in `tests/contract/test_auth_session.py`, per spec BE-001
- [X] T024 [P] [US1] (backend) Regression contract test confirming `POST /auth/login`'s request/response shape
  is byte-for-byte unchanged from Feature 001, in `tests/contract/test_auth_login_unchanged.py`, per spec
  BE-002/SC-002
- [X] T025 [P] [US1] (backend) Integration test: web register → `POST /auth/session` → `GET /users/me` succeeds
  using only the cookie (no `Authorization` header sent at all), in
  `tests/integration/test_web_login_flow.py`, per spec US1 AC2
- [X] T026 [P] [US1] (frontend) Component test for the Login page: valid submit redirects to the dashboard;
  invalid credentials show the generic error message, in `frontend/tests/pages/Login.test.tsx`
- [X] T027 [P] [US1] (frontend) Component test for the Register page: valid submit navigates to login;
  duplicate-email and password-length-policy errors are both displayed distinctly, in
  `frontend/tests/pages/Register.test.tsx`

### Implementation for User Story 1

- [X] T028 [US1] (backend) Implement `POST /auth/session` in `src/api/auth.py`: calls the existing
  `auth_service.login()` internally, then sets the `session_id` and `csrf_token` cookies
  (`HttpOnly`/`Secure={settings.cookie_secure}`/`SameSite=Lax`, `Max-Age` aligned to `Session.expires_at`) and
  returns `WebSessionResponse` with no token field, per spec BE-001 (depends on T015; adds to the already-
  registered `auth` router, so no `main.py` change is needed)
- [X] T029 [P] [US1] (frontend) Implement the Landing page in `frontend/src/pages/Landing.tsx`
- [X] T030 [US1] (frontend) Implement the Login page in `frontend/src/pages/Login.tsx` calling
  `POST /auth/session` via a TanStack Query mutation, using the API client (T017) and populating the auth
  context (T018) on success
- [X] T031 [US1] (frontend) Implement the Register page in `frontend/src/pages/Register.tsx` (same directory as
  T030, different file) calling `POST /auth/register` (unchanged Feature 001 endpoint) via a TanStack Query
  mutation

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - View Dashboard and Profile, Log Out (Priority: P1)

**Goal**: Any logged-in user can view a dashboard and their own profile, and log out — ending the session on
both the browser and the server.

**Independent Test**: Log in, view dashboard/profile, log out, confirm the browser can no longer reach either
without logging in again.

### Tests for User Story 2 ⚠️

- [X] T032 [P] [US2] (backend) Contract test: cookie-authenticated `POST /auth/logout` with a valid matching
  `X-CSRF-Token` succeeds (`204`) and clears both cookies; with a missing/mismatched token, rejected
  (`403 {"error":"csrf_token_invalid"}`), in `tests/contract/test_auth_logout_csrf.py`, per spec BE-004
- [X] T033 [P] [US2] (backend) Contract test confirming a bearer-authenticated `POST /auth/logout` succeeds with
  no CSRF header at all, in the same test file as T032, per spec BE-007
- [X] T034 [P] [US2] (frontend) Component test for the Profile page: renders the current user's own
  email/role/status/created_at and nothing else, in `frontend/tests/pages/Profile.test.tsx`
- [X] T035 [P] [US2] (frontend) Component test for the logout action: clicking logout clears local auth state
  and redirects to login, in `frontend/tests/components/Logout.test.tsx`

### Implementation for User Story 2

- [X] T036 [US2] (backend) Extend `POST /auth/logout` in `src/api/auth.py` to resolve the session via
  cookie-or-header (T013), require `require_csrf` (T014) only when cookie-authenticated, and clear the
  `session_id`/`csrf_token` cookies in the response, per spec BE-004 (depends on T013, T014)
- [X] T037 [P] [US2] (frontend) Implement the Dashboard shell page in `frontend/src/pages/Dashboard.tsx` using
  the AppShell (T021)
- [X] T038 [US2] (frontend) Implement the Profile page in `frontend/src/pages/Profile.tsx` (same directory as
  T037, different file) calling `GET /users/me` via TanStack Query
- [X] T039 [US2] (frontend) Implement the logout action (button + handler) wired into AppShell
  (`frontend/src/components/AppShell.tsx`, same file as T021 — run after it), calling `POST /auth/logout` via
  the API client and clearing the auth context on success

**Checkpoint**: User Story 2 is fully functional and independently testable.

---

## Phase 5: User Story 3 - Backend-Enforced Role-Based Navigation (Priority: P1)

**Goal**: Frontend navigation reflects role as a convenience; the backend independently enforces every
authorization decision regardless of what the frontend displays.

**Independent Test**: Confirm navigation differs per role; separately, issue a direct request for an
Admin-only action as a Citizen and confirm the backend rejects it regardless of frontend state.

### Tests for User Story 3 ⚠️

- [X] T040 [P] [US3] (backend) Integration test: a Citizen with a valid cookie session directly calls an
  Admin-only endpoint (bypassing any frontend route), confirming `403`, in
  `tests/integration/test_role_nav_backend_enforcement.py`, per spec US3 AC3/SC-008

### Implementation for User Story 3

- [X] T041 [US3] (frontend) Apply the role-aware route guards (T019) to every Admin-only frontend route (user
  management, audit log), redirecting Citizen/Officer away, in `frontend/src/routes/index.tsx` (same file as
  T019 — run after it)
- [X] T042 [P] [US3] (frontend) Implement a "Forbidden" page/component shown when the API client (T017) reports
  a `403`, in `frontend/src/pages/Forbidden.tsx`, per spec FE-019

**Checkpoint**: User Story 3 is fully functional and independently testable.

---

## Phase 6: User Story 4 - CSRF-Protected State-Changing Requests (Priority: P1)

**Goal**: Every cookie-authenticated state-changing request requires a matching anti-CSRF token; bearer-authenticated
requests are exempt.

**Independent Test**: A cookie-authenticated mutation with a missing/mismatched token is rejected; the same
mutation with a valid token succeeds; an equivalent bearer-authenticated mutation succeeds with no token at all.

### Tests for User Story 4 ⚠️

- [X] T043 [P] [US4] (backend) Unit tests for `csrf_service.generate_csrf_token()`/`verify_csrf_token()` covering
  match, mismatch, and missing-value cases, in `tests/unit/test_csrf_service.py`
- [X] T044 [P] [US4] (backend) Contract test: cookie-authenticated `PATCH /admin/users/{id}/role` and
  `PATCH /admin/users/{id}/status` both reject a missing/mismatched `X-CSRF-Token` with
  `403 {"error":"csrf_token_invalid"}`, and both succeed with a valid matching token, in
  `tests/contract/test_admin_csrf.py`, per spec BE-006
- [X] T045 [P] [US4] (backend) Contract test confirming bearer-authenticated calls to the same two endpoints
  succeed with no CSRF header at all, in the same test file as T044, per spec BE-007/SEC-004

### Implementation for User Story 4

- [X] T046 [US4] (backend) Apply the `require_csrf` dependency (T014) to
  `PATCH /admin/users/{user_id}/role` in `src/api/admin.py`, active only when the request was
  cookie-authenticated
- [X] T047 [US4] (backend) Apply the `require_csrf` dependency (T014) to
  `PATCH /admin/users/{user_id}/status` in `src/api/admin.py` (same file as T046 — run after it)
- [X] T048 [P] [US4] (frontend) Add a regression test confirming the API client (T017) attaches
  `X-CSRF-Token` automatically to every `POST`/`PATCH`/`PUT`/`DELETE` request made under a cookie session, with
  no per-call-site code required, in `frontend/tests/api/client.test.ts`

**Checkpoint**: User Story 4 is fully functional and independently testable; every cookie-authenticated mutation
in the system is now CSRF-protected.

---

## Phase 7: User Story 5 - Admin Searches, Filters, and Paginates the User List (Priority: P2)

**Goal**: An Admin can find a specific user via search, role filter, and status filter, paging through results.

**Independent Test**: Search, filter, and page through users as Admin; confirm no password/session/token data
ever appears.

### Tests for User Story 5 ⚠️

- [X] T049 [P] [US5] (backend) Contract test for `GET /admin/users`: partial case-insensitive email search, role
  filter, status filter, each returning only safe fields, in `tests/contract/test_admin_users_list.py`, per spec
  BE-008/BE-009
- [X] T050 [P] [US5] (backend) Contract test for pagination: default `page=1`/`page_size=20`, out-of-bounds
  `page`/`page_size` → `422`, non-Admin caller → `403`, in the same test file as T049
- [X] T051 [P] [US5] (frontend) Component test for the Admin Users page: renders a result row per item, shows
  the empty state on no matches, and shows pagination controls reflecting `total`/`page`/`page_size`, in
  `frontend/tests/pages/AdminUsers.test.tsx`

### Implementation for User Story 5

- [X] T052 [US5] (backend) Implement `src/application/user_query_service.py`: search/filter/paginate logic
  querying `UserAccount` (case-insensitive email search per existing FR-029 normalization, optional role/status
  filters, `page`/`page_size` per research.md), returning `(items, total)` (depends on T016)
- [X] T053 [US5] (backend) Implement `GET /admin/users` in `src/api/admin.py` using `require_admin` and
  `user_query_service`, per spec BE-008 (depends on T052)
- [X] T054 [P] [US5] (frontend) Implement the Admin Users page in `frontend/src/pages/admin/Users.tsx` with a
  search input, role/status filter controls, and pagination controls, using TanStack Query and the shared
  Loading/Error/Empty primitives (T020)

**Checkpoint**: User Story 5 is fully functional and independently testable.

---

## Phase 8: User Story 6 - Admin Changes Roles and Enables/Disables Accounts via the Web UI (Priority: P2)

**Goal**: From the Admin Users page, an Admin can change a user's role or enable/disable their account, with
rejection reasons (self-targeting, last-admin invariant) surfaced clearly.

**Independent Test**: Change another user's role/status and confirm it takes effect; attempt self-targeting or
last-admin removal and confirm the specific rejection reason is shown.

### Tests for User Story 6 ⚠️

- [X] T055 [P] [US6] (frontend) Component test: changing a user's role or status from the Admin Users page
  succeeds and the updated value is reflected immediately; a self-targeted or last-admin-violating attempt
  displays the specific backend-provided reason rather than a generic error, in
  `frontend/tests/pages/AdminUsersActions.test.tsx`, per spec FE-011/FE-012

### Implementation for User Story 6

- [X] T056 [US6] (frontend) Add role-change and status-toggle controls to the Admin Users page
  (`frontend/src/pages/admin/Users.tsx`, same file as T054 — run after it), calling the existing
  `PATCH /admin/users/{id}/role`/`status` endpoints (CSRF-protected per US4) via the API client, displaying the
  exact `error` value from a `403`/`409` response

**Checkpoint**: User Story 6 is fully functional and independently testable.

---

## Phase 9: User Story 7 - Admin Views and Filters the Audit Log via the Web UI (Priority: P2)

**Goal**: An Admin can browse and filter the existing audit trail through the web UI.

**Independent Test**: Perform a role/status change, then find both corresponding entries using the audit log
view's filters.

### Tests for User Story 7 ⚠️

- [X] T057 [P] [US7] (frontend) Component test for the Audit Log page: renders entries with
  actor/action/affected-user/timestamp, supports filtering by affected user, action type, and time range, in
  `frontend/tests/pages/AdminAuditLog.test.tsx`, per spec FE-013

### Implementation for User Story 7

- [X] T058 [US7] (frontend) Implement the Admin Audit Log page in `frontend/src/pages/admin/AuditLog.tsx`
  calling the existing, unchanged `GET /admin/audit-log` endpoint (with its existing filters) via TanStack Query

**Checkpoint**: User Story 7 is fully functional and independently testable.

---

## Phase 10: User Story 8 - Request and Complete Password Reset via Real Email (Priority: P2)

**Goal**: A real, usable password-reset flow — actual email delivery, not a log-only stand-in.

**Independent Test**: Request a reset for a reachable test address, retrieve the delivered message, follow its
link, submit a new password, log in with it.

### Tests for User Story 8 ⚠️

- [X] T059 [P] [US8] (backend) Unit test for the real email-sending implementation (against a test-capturable
  SMTP target) asserting a message is actually dispatched and contains the reset link, in
  `tests/unit/test_email_delivery.py`, per spec BE-010
- [X] T060 [P] [US8] (backend) Integration test confirming the existing single-use/expiring reset-token
  behavior (Feature 001 FR-010a) is unchanged with the real send path in place, in
  `tests/integration/test_password_reset_real_email.py`
- [X] T061 [P] [US8] (frontend) Component test for the Forgot Password page: submitting shows the identical
  generic confirmation regardless of outcome, in `frontend/tests/pages/ForgotPassword.test.tsx`, per spec FE-005
- [X] T062 [P] [US8] (frontend) Component test for the Reset Password page: reads the token from the URL query
  string, submits a new password meeting the length policy, and shows a specific error for an expired/used
  token, in `frontend/tests/pages/ResetPassword.test.tsx`, per spec FE-006

### Implementation for User Story 8

- [X] T063 [US8] (backend) Replace the log-only stub in `src/infrastructure/email.py` with a real
  `smtplib`-based send invoked via `starlette.concurrency.run_in_threadpool`, using the new SMTP settings (T009),
  preserving the existing seam signature `send_password_reset_email(to_email, reset_link)`, per spec
  BE-010/BE-011
- [X] T064 [P] [US8] (frontend) Implement the Forgot Password page in `frontend/src/pages/ForgotPassword.tsx`
  calling the existing, unchanged `POST /auth/password-reset/request`
- [X] T065 [US8] (frontend) Implement the Reset Password page in `frontend/src/pages/ResetPassword.tsx` (same
  directory as T064, different file) reading `token` from the URL query string and calling the existing,
  unchanged `POST /auth/password-reset/confirm`

**Checkpoint**: User Story 8 is fully functional and independently testable.

---

## Phase 11: User Story 9 - Citizen and Officer Basic Dashboards (Priority: P3)

**Goal**: Citizens and Officers each see a structurally identical basic dashboard showing only their own
profile/account information.

**Independent Test**: Log in as each role and confirm identical dashboard structure, each showing that role's own
(different) data.

### Tests for User Story 9 ⚠️

- [X] T066 [P] [US9] (frontend) Component test confirming the Citizen and Officer dashboards render an
  identical structure, each showing only that user's own account information, in
  `frontend/tests/pages/BasicDashboard.test.tsx`

### Implementation for User Story 9

- [X] T067 [US9] (frontend) Implement a shared `BasicDashboard` component in
  `frontend/src/components/BasicDashboard.tsx` (profile + account information only) used identically by both the
  Citizen and Officer dashboard routes

**Checkpoint**: User Story 9 is fully functional and independently testable.

---

## Phase 12: User Story 10 - Correct Rate Limiting Behind a Reverse Proxy (Priority: P3)

**Goal**: The existing per-source-IP rate limiter keys on the real client address behind a trusted reverse
proxy, and never trusts a forwarded header from an untrusted source.

**Independent Test**: Simulate requests through a trusted-proxy address carrying different forwarded addresses
and confirm independent limiting; separately confirm an untrusted source's forwarded header is ignored.

### Tests for User Story 10 ⚠️

- [X] T068 [P] [US10] (backend) Unit tests constructing an ASGI scope with a trusted connecting-peer address,
  asserting the middleware (T010) rewrites `scope["client"]` to the forwarded address for (a) a single-value
  `X-Forwarded-For` header and (b) a comma-separated multi-value header, confirming only the rightmost value is
  used in case (b) — not the full header string — in `tests/unit/test_trusted_proxy_middleware.py`, per spec
  BE-014
- [X] T069 [P] [US10] (backend) Unit test constructing an ASGI scope with an untrusted connecting-peer address
  and the same header, asserting the header is ignored and the original peer address is kept, in the same test
  file as T068, per spec BE-015
- [X] T070 [P] [US10] (backend) Integration test simulating registration/password-reset-request traffic through
  a configured trusted-proxy address with two different forwarded client addresses, confirming each is
  rate-limited independently, in `tests/integration/test_rate_limit_behind_proxy.py`, per spec
  BE-016/US10 AC1/AC4

### Implementation for User Story 10

- [X] T071 [US10] (docs) Add a deployment-configuration note to `README.md` (or a new `docs/deployment.md`)
  documenting: how to set `TRUSTED_PROXY_IPS` to the real reverse-proxy address(es) in production; the risk of
  leaving it unset behind a proxy (shared-IP rate limiting, per Feature 002's Conflict B); and the requirement
  that the reverse proxy itself must be configured to **append** the real observed client address as a new,
  rightmost `X-Forwarded-For` entry (overwriting or discarding any value a client sent directly), never blindly
  relay a client-supplied header verbatim — since this feature's middleware trusts the rightmost entry precisely
  because a correctly-configured proxy is the one that put it there

**Checkpoint**: User Story 10 is fully functional and independently testable.

---

## Phase 13: User Story 11 - Cookie Security Configuration Fails Closed in Production (Priority: P3)

**Goal**: The system refuses to start with a missing or insecure `COOKIE_SECURE` value in production.

**Independent Test**: Attempt to start with `environment=production, COOKIE_SECURE=false` and confirm refusal;
confirm `development`+`false` and `production`+`true` both start normally.

### Tests for User Story 11 ⚠️

- [X] T072 [P] [US11] (backend) Unit test: `Settings(environment="production", cookie_secure=False)` raises at
  construction, in `tests/unit/test_cookie_secure_fail_closed.py`, per spec BE-013
- [X] T073 [P] [US11] (backend) Unit test: `Settings(environment="development", cookie_secure=False)`
  constructs successfully, in the same test file as T072
- [X] T074 [P] [US11] (backend) Unit test: `Settings()` with `cookie_secure` entirely unset raises at
  construction in any environment, in the same test file as T072, per spec BE-012

### Implementation for User Story 11

- [X] T075 [US11] (docs) Update `.env.example` and `README.md` to state that `COOKIE_SECURE=true` is a hard
  requirement for any production deployment

**Checkpoint**: User Story 11 is fully functional and independently testable; all eleven user stories complete.

---

## Phase 14: Polish & Cross-Cutting Concerns

- [X] T076 [P] Run quickstart.md scenarios 1–4 and 6–8 end-to-end against a running backend + frontend dev
  instance and record results. Scenario 5 (trusted-proxy client-IP handling) is explicitly **not** validated by
  this task — quickstart.md itself states it is not practically demonstrable via curl/browser testing; T068–T070
  (dedicated middleware/integration tests) and T071 (deployment-configuration verification) remain the
  authoritative proof for that behavior
- [X] T077 [P] (backend) Run Feature 001's complete existing test suite and confirm zero regressions, per spec
  SC-002
- [X] T078 [P] (frontend) Accessibility pass across all new frontend pages: confirm every interactive control is
  keyboard-operable and exposes an accessible name, per spec FE-017
- [X] T079 [P] (frontend) Responsive-layout check across a mobile-width and a desktop-width viewport for every
  in-scope page, per spec FE-016/SC-010
- [X] T080 [P] (frontend) Add `frontend/README.md` documenting setup, dev-server (with proxy), build, and test
  commands
- [X] T081 [P] Run lint/format across both the backend's new/changed files and the frontend, per the
  constitution's Development Principles
- [X] T082 (docs) Update the root `README.md`'s Feature documentation section to list
  `specs/002-web-frontend-auth`'s artifacts alongside Feature 001's

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–13)**: All depend on Foundational completion; P1 stories (US1–US4) should complete
  before P2 (US5–US8), which should complete before P3 (US9–US11), though P2/P3 stories are independently
  testable once Foundational is done if staffed in parallel
- **Polish (Phase 14)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: True MVP — no dependency on other stories
- **US2 (P1)**: Independent of US1 at the data layer; shares the Dashboard/AppShell foundation
- **US3 (P1)**: Independent; depends on Foundational's route-guard setup (T019) and the admin-protected routes
  US5/US7 will later add — its own test (T040) only needs *an* existing Admin-only endpoint, already present
  from Feature 001
- **US4 (P1)**: Independent; applies to endpoints that already exist (logout from US2, role/status-change from
  Feature 001) — should land before or alongside US2/US6 so cookie-authenticated mutations are never
  unprotected in practice
- **US5 (P2)**: Independent new endpoint + page; no dependency on US6/US7
- **US6 (P2)**: Builds on US5's Admin Users page (same file, later task) and US4's CSRF protection
- **US7 (P2)**: Independent; only needs Foundational
- **US8 (P2)**: Independent; only needs Foundational
- **US9 (P3)**: Independent; only needs the common authenticated shell (US2)
- **US10 (P3)**: Independent; Foundational's middleware (T010/T011) already implements the mechanism — this
  story is its dedicated test/verification/documentation deliverable
- **US11 (P3)**: Independent; Foundational's validator (T007) already implements the mechanism — this story is
  its dedicated test/verification/documentation deliverable

### Within Each User Story

- Tests MUST be written first and FAIL before implementation
- Backend before frontend where a frontend task consumes a backend endpoint from the same story
- Story complete and checkpointed before moving to the next priority tier

### Parallel Opportunities

- Setup: T005, T006 can run in parallel with each other (T001–T004 share `package.json`, sequential)
- Foundational: T010, T012, T015, T017, T018, T019, T020, T021 can run in parallel once their individual
  dependencies are met (different files)
- Once Foundational completes, independent stories (US1, US5, US7, US8, US9, US10, US11) can be staffed in
  parallel; US2/US3/US4/US6 follow the ordering notes above
- All test tasks within a story marked [P] can run in parallel with each other

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /auth/session in tests/contract/test_auth_session.py"
Task: "Regression contract test for POST /auth/login in tests/contract/test_auth_login_unchanged.py"
Task: "Integration test for cookie-only web login flow in tests/integration/test_web_login_flow.py"
Task: "Component test for Login page in frontend/tests/pages/Login.test.tsx"
Task: "Component test for Register page in frontend/tests/pages/Register.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: register → cookie-login → access a protected page using only the cookie; confirm the
   existing bearer-token contract is untouched
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test independently → MVP (cookie login works, bearer compatibility proven)
3. US4 → test independently (CSRF protection exists before any mutation ships unprotected)
4. US2 → test independently (dashboard/profile/logout, now CSRF-safe)
5. US3 → test independently (role-nav is UX-only, backend independence proven)
6. US5 → test independently (admin can find users)
7. US6 → test independently (admin can act on users)
8. US7 → test independently (admin audit log UI)
9. US8 → test independently (real password-reset email)
10. US9 → test independently (citizen/officer dashboards)
11. US10 → test independently (trusted-proxy correctness)
12. US11 → test independently (cookie-secure fail-closed)
13. Phase 14: Polish

### Parallel Team Strategy

With multiple developers, after Foundational:

- Developer A (backend-leaning): US1 → US4 → US10 → US11
- Developer B (frontend-leaning): US2 → US3 → US9
- Developer C: US5 → US6 → US7
- Developer D: US8 (password reset, fully independent, touches both stacks)

---

## Notes

- [P] tasks touch different files and have no incomplete-task dependency between them
- [Story] label maps each task to its spec.md user story for traceability
- Every task's description is also explicitly labeled (backend)/(frontend)/(docs) per the instruction to keep
  the two clearly separated
- Verify each test fails before implementing against it
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts marked [P], cross-story dependencies that break independent testability

---

## Phase 15: Convergence

- [X] T083 [US1] (frontend) Add a `429`-specific "too many attempts, try again later" message to the Register
  page's error handling in `frontend/src/pages/Register.tsx` (currently falls through to a generic error on
  `429`) per FE-020 (missing)
- [X] T084 [US3] (frontend) Render an explicit "you don't have permission for this" state when a query fails with
  `403` in `frontend/src/pages/admin/Users.tsx` and `frontend/src/pages/admin/AuditLog.tsx` (currently both show
  the generic `ErrorState` for any query error) per FE-019/SEC-003/US3 AC4 (partial)
- [X] T085 [US8] (frontend) In `frontend/src/pages/ResetPassword.tsx`, distinguish a `422` password-policy error
  from a `400` invalid/expired-token error instead of showing "This reset link is invalid or has expired" for
  both per US8 AC4 (partial)
- [X] T086 [US7] (frontend) Make the Audit Log's "affected user" filter in `frontend/src/pages/admin/AuditLog.tsx`
  usable without an Admin already knowing a raw UUID — either surface each user's id somewhere reachable from
  `frontend/src/pages/admin/Users.tsx`, or change the filter to resolve by email per FE-013/US7 (partial)
- [X] T087 (backend) Reconcile `src/infrastructure/email.py::send_password_reset_email` with the recorded design
  decision in research.md/plan.md ("invoked through Starlette's `run_in_threadpool`") and T063 — either wrap the
  `smtplib` call in `run_in_threadpool`, or update research.md/plan.md to record the actual synchronous-seam
  decision and why per plan.md "Email delivery mechanism" (contradicts)
