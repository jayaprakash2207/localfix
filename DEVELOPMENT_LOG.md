# LocalFix — Development Log

A narrative record of how this project was built, end to end, using GitHub's Spec Kit
(Spec-Driven Development) workflow with Claude Code. For the raw, unedited back-and-forth,
see [docs/conversation-transcript.md](docs/conversation-transcript.md).

## Starting point

The project began as an empty directory with no tools installed — no Python, no `uv`, no
`git` on PATH, and no admin rights available on the machine. Every tool used below (Python,
`uv`, Node.js, PostgreSQL) was installed through non-admin-requiring means: portable ZIP
distributions extracted to short paths, or `winget`'s user-scope install mode, with PATH
changes persisted at the user (HKCU) registry scope rather than machine-wide.

## Feature 001 — Authentication and RBAC

**Spec-Driven Development lifecycle**: `/speckit-constitution` → `/speckit-specify` →
`/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` →
`/speckit-converge` → `/speckit-implement` (closing gaps) → `/speckit-converge` (clean).

**What was built**: A FastAPI + SQLAlchemy + Alembic + PostgreSQL backend implementing:

- Registration, login, logout, self-profile viewing, and password reset for three roles
  (Citizen, Officer, Admin)
- Argon2id password hashing (OWASP's current recommendation)
- Opaque, server-revocable session tokens (SHA-256 hashed at rest, never JWT) so logout and
  account-disable can invalidate a session instantly
- Per-account brute-force lockout (5 consecutive failures → 15-minute cooldown), checked
  *before* password verification so a locked-out account and a wrong password are
  indistinguishable to a caller
- A last-ACTIVE-Admin invariant: the system can never end up with zero active Admins,
  enforced with `SELECT ... FOR UPDATE` row-locking across the full admin set to close a
  TOCTOU race that an earlier version of the check missed
- A full audit trail (actor, action, affected user, timestamp) for every security-sensitive
  action
- Layered architecture: `src/api` (presentation) → `src/application` (business logic) →
  `src/domain` (framework-free types) → `src/infrastructure` (data access, security, config)

**Formal security review**: after the initial implementation converged cleanly, a dedicated
security-review pass found 13 findings (F1–F13), the most serious being a login-timing side
channel (verified empirically: timing differed measurably between "no such account" and
"wrong password" before a dummy-hash step was added to equalize them) and the TOCTOU race in
the last-admin invariant mentioned above. All 13 were fed back through the SDD cycle as new
functional requirements and a "Security Hardening Addendum" in the plan, then implemented
and verified — including deliberately *breaking* each fix temporarily to confirm the
corresponding test actually caught the regression, before restoring it.

**Final state**: 105/105 tasks complete, 87 tests passing, clean lint, no DB migration drift.

## Feature 002 — LocalFix Frontend and Web Authentication

**Scope**: a React/TypeScript/Vite/Tailwind frontend consuming Feature 001's backend, plus
the backend extensions needed to serve it: cookie-based web sessions alongside the unchanged
bearer-token API, CSRF protection, an Admin user-management UI, real password-reset email
delivery, and correct rate-limiting behind a reverse proxy.

**Design decisions, made explicitly before any code was written** (the user drove this
through several rounds of numbered decisions, captured in full in the transcript):

- Dual session transport: `Authorization: Bearer` header checked first (so any existing
  non-browser client is completely unaffected), falling back to a `session_id` cookie
- The cookie is `HttpOnly`; the browser's JavaScript never sees the raw session token at any
  point in the web login flow
- `SameSite=Lax` always; `Secure` controlled by an explicit `COOKIE_SECURE` setting with **no
  default** — the app refuses to start in production if it's left unset or set to `false`
- Double-submit-cookie CSRF (no server-side storage) on cookie-authenticated state-changing
  requests only; bearer-authenticated requests are exempt, since they can't be forged
  cross-site in the first place
- Same-origin everywhere — a Vite dev-server proxy in development, a reverse proxy in
  production — so no CORS is needed on the normal path
- An explicit `TRUSTED_PROXY_IPS` allow-list so the existing rate limiter can correctly
  identify real client IPs behind a reverse proxy, never trusting `X-Forwarded-For` from an
  unconfigured source, and correctly taking the *rightmost* value of a multi-hop header
  rather than treating the whole header as one IP

**SDD lifecycle**: `/speckit-specify` → `/speckit-plan` → a dedicated pre-implementation
consistency check (which caught two real gaps before any code was written: incomplete
multi-value `X-Forwarded-For` handling, and a task description that overclaimed what could
be verified by browser/curl testing) → `/speckit-tasks` (82 tasks across 11 user stories) →
`/speckit-implement` → `/speckit-converge` (found 5 gaps) → `/speckit-implement` (closed all
5).

**Real bugs found during implementation** (not just planned work):

1. `POST /auth/logout` 500'd on a cookie-only request — it unconditionally required a
   `Bearer` header even after cookie-based sessions were added. Fixed by resolving the
   session the same way `get_current_user` does, with the resolved auth transport and raw
   token threaded through `request.state` so `logout` and `require_csrf` don't each
   re-implement the resolution.
2. Live end-to-end testing of the real SMTP path (not just mocked tests) surfaced that the
   dev `.env`'s placeholder `SMTP_USERNAME=test`/`SMTP_PASSWORD=test` caused the app to
   attempt `AUTH` against a local no-auth-required SMTP sink, breaking password reset
   entirely. The application code was already correct (it only attempts login when both
   credentials are non-empty); the fix was the dev configuration, plus a regression test for
   the skip-auth branch so this can't silently regress.
3. A Vitest/`@vitest/spy` interaction: a `beforeEach(() => mock.mockReset())` combined with a
   later rejecting mock in the same test file caused spurious test failures with no
   corresponding code bug — tracked down through a sequence of isolated minimal
   reproductions (documented in the transcript) before the actual trigger (the `mockReset`
   itself, not anything about the rejection) was identified and removed.

**Convergence findings** (gaps the implementation had relative to spec.md/plan.md that the
task list alone didn't fully capture), all closed in a second implement pass:

- Registration page was missing the `429` "too many attempts" message the spec explicitly
  requires (it existed on the Forgot Password page but not Register)
- Admin pages fell back to a generic error message on `403` instead of the spec's required
  explicit "not permitted" wording
- The Reset Password page showed "link is invalid or expired" for *every* error, including a
  `422` password-policy violation that had nothing to do with the link
- The Audit Log's "affected user" filter required typing a raw UUID that nothing in the UI
  ever displayed — fixed by resolving an entered email to a user id via the existing
  user-search endpoint before querying
- The actual SMTP implementation didn't match the literal wording of an earlier planning
  decision (`run_in_threadpool`); traced the real call chain, determined the literal wording
  would have required making a Feature-001-tested synchronous seam asynchronous for no actual
  concurrency benefit (FastAPI already dispatches synchronous routes to a worker thread), and
  updated the planning documents to record the *actual*, reasoned decision instead of forcing
  an unnecessary and regression-risking code change

**Final state**: 87/87 tasks complete (82 original + 5 convergence), 135/135 backend tests
passing, 34/34 frontend tests passing, both lints clean, both builds clean. Manually
validated live against a running backend + frontend dev server + a local SMTP sink: cookie
login with no raw token exposed, bearer-auth backward compatibility, CSRF enforcement (both
the reject and accept paths, and the bearer exemption), admin user search/filter/pagination,
`COOKIE_SECURE` fail-closed behavior, and real SMTP password-reset delivery.

## Process notes

- Every implementation task followed the same discipline: write the test first, confirm it
  fails for the right reason (not a typo or setup bug), implement, confirm it passes, run the
  *full* test suite (not just the new tests) plus lint before marking the task done.
- `/speckit-converge` was run after each `/speckit-implement` pass specifically to catch the
  gap between "the task list is complete" and "the spec is actually satisfied" — both
  convergence runs in this project found real, concrete gaps that a task-completion check
  alone would have missed.
