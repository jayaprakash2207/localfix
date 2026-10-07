# Phase 0 Research: LocalFix Frontend and Web Authentication

Every Technical Context item was either specified directly (React/TypeScript/Vite/Tailwind/TanStack Query,
cookie-based auth, SameSite=Lax, double-submit CSRF, Vite-proxy dev / reverse-proxy prod architecture,
page/page_size pagination style) or resolved below. No `NEEDS CLARIFICATION` markers remain.

## CSRF mechanism implementation

- **Decision**: Hand-rolled double-submit-cookie check — a small FastAPI dependency comparing an `X-CSRF-Token`
  request header against a `csrf_token` cookie value, applied only when the request was authenticated via the
  session cookie (not the bearer header). No new dependency.
- **Rationale**: The mechanism itself (compare two values) is a few lines; the codebase already favors
  hand-rolled, explicit services over libraries for comparably small cross-cutting concerns (`rate_limit_service.py`,
  the login-lockout counter). A CSRF library would add a dependency to save perhaps ten lines of code.
- **Alternatives considered**: `fastapi-csrf-protect` (a third-party library) — rejected as unjustified added
  dependency for logic this simple, consistent with the constitution's "avoid unnecessary complexity."

## Trusted-proxy client-IP resolution

- **Decision**: A small, explicit ASGI middleware in `src/infrastructure/security/trusted_proxy.py`, wired into
  `main.py`, driven by the new `TRUSTED_PROXY_IPS` setting (empty by default). It rewrites `scope["client"]` from
  the `X-Forwarded-For` header **only** when the immediate connecting peer's address is in the configured list;
  otherwise the scope is left untouched. Because `rate_limit_service.py` and `dependencies.py` already read "the
  request's client IP" generically via `request.client.host` — a Starlette property that reads directly from
  `scope["client"]` — **no changes are needed in either file**: both transparently see the corrected address once
  this middleware has run, confirmed by inspecting `dependencies.py::rate_limited`'s existing
  `request.client.host` usage.
  **`X-Forwarded-For` parsing**: this header may legitimately contain a comma-separated chain (e.g.,
  `"203.0.113.5, 10.0.0.2"`) when multiple hops are involved. The approved production architecture (plan.md) has
  exactly one reverse proxy in front of the app, so the middleware takes the **rightmost** (last) comma-separated
  value — the address the trusted proxy itself observed and appended — trims surrounding whitespace, and uses
  that as the corrected client address. It never treats the full header string as a single IP, and it never
  trusts anything other than that single trusted hop's own contribution to the header (a multi-hop/multiple-
  trusted-proxies topology is out of scope for this feature's single-reverse-proxy architecture, matching
  plan.md's Deployment Architecture, and would need its own decision if that architecture changes).
- **Rationale**: Fail-closed by construction — an empty/unset `TRUSTED_PROXY_IPS` means forwarded headers are
  never honored, so a misconfigured deployment reverts to today's known (shared-proxy-IP) limitation rather than
  the strictly worse failure mode of trusting an arbitrary client-supplied header.
- **Alternatives considered**: uvicorn's built-in `--forwarded-allow-ips` CLI flag — does the same job at the
  server-launch layer instead of in application code. Rejected in favor of in-app middleware because it's
  directly unit-testable at the ASGI-scope level (constructing a scope with a given peer + header and asserting
  the rewrite behavior), whereas verifying a CLI flag's effect requires a running server process per test.

## Email delivery mechanism

- **Decision**: Python's standard-library `smtplib`, called synchronously, replacing the existing log-only stub
  behind the same `send_password_reset_email(to_email, reset_link)` seam, unchanged in signature and sync-ness.
  SMTP host/port/credentials become new, required environment configuration.
- **Revised during implementation**: an earlier draft of this decision named `starlette.concurrency.run_in_threadpool`
  explicitly, to keep the blocking SMTP I/O off the asyncio event loop. That turned out to be unnecessary *and*
  actively harmful once the actual call path was traced: `send_password_reset_email` is only ever invoked from
  `password_reset_service.request_reset`, which is only ever invoked from `POST /auth/password-reset/request` —
  a plain synchronous FastAPI route (`def`, not `async def`). FastAPI/Starlette already dispatches every
  synchronous route handler to a worker thread via its own internal `run_in_threadpool` call
  (`fastapi/routing.py::run_endpoint_function`) before it ever runs. By the time `send_password_reset_email`
  executes, the code is already off the event-loop thread — wrapping the `smtplib` call in a *second*,
  redundant `run_in_threadpool` call would add complexity (and would require making the seam `async`, which
  Feature 001's existing tests monkeypatch as a plain synchronous function — `tests/contract/test_password_reset_request.py`,
  `tests/contract/test_password_reset_confirm.py`, `tests/contract/test_password_policy.py`,
  `tests/integration/test_password_reset_flow.py`, `tests/integration/test_password_reset_edge_cases.py`,
  `tests/integration/test_audit_trail_completeness.py` — making it `async` would break all six without any
  corresponding safety benefit) for zero actual concurrency benefit.
- **Rationale**: Every mainstream transactional-email provider (SES, SendGrid, Postmark, Mailgun, a corporate
  Exchange/Postfix server) exposes an SMTP endpoint, so targeting SMTP directly — rather than a
  provider-specific SDK — satisfies "keep the email provider implementation flexible" at the protocol level: no
  vendor-specific client library, no vendor lock-in in the code, and switching providers later is purely a
  configuration change (point `SMTP_HOST` elsewhere), not a code change. No new dependency (stdlib only).
- **Alternatives considered**: A provider-specific SDK (e.g., `boto3` for SES) — rejected because it hard-codes
  one vendor into the code, directly contradicting the "flexible" requirement. An async-native SMTP library
  (`aiosmtplib`) — rejected to avoid adding a dependency; stdlib `smtplib` is sufficient since the call is
  already off the event loop by construction (see above). Wrapping in `run_in_threadpool` anyway, purely for
  documentation-literal consistency — rejected as unjustified complexity with a concrete regression cost and no
  behavioral benefit, which the constitution's Development Principles weigh against.

## Dual bearer/cookie session resolution order

- **Decision**: `get_current_user` checks the `Authorization` header first; only if absent does it check the
  session cookie. (Already specified in spec BE-003; recorded here for the implementation-level rationale.)
- **Rationale**: Guarantees zero behavior change for any client that already sends a header — the safest possible
  backward-compatibility posture for Feature 001's existing, already-tested contract.
- **Alternatives considered**: Cookie-first — rejected; would subtly change precedence for a hypothetical client
  that (incorrectly) sent both, with no benefit.

## Admin user-listing pagination defaults

- **Decision**: `page` defaults to `1` (minimum `1`); `page_size` defaults to `20` (minimum `1`, maximum `100`).
  Values outside bounds → `422`, matching the existing validation pattern used everywhere else in this API.
- **Rationale**: 20 is a comfortable default table-page size for a human admin scanning results; 100 caps a
  single response at a size that stays fast and hard to abuse, consistent with the audit-log endpoint's existing
  flat 500-row cap philosophy (bounded, not unlimited).
- **Alternatives considered**: Cursor-based pagination — rejected per the approved proposal's explicit
  preference for page/page_size at this scale (low thousands of accounts), where offset pagination's usual
  downsides (skipped/duplicated rows under concurrent writes) are not a practical concern.

## Frontend routing

- **Decision**: React Router (client-side routing) for the multi-page SPA (landing, login, register,
  forgot/reset password, dashboard, profile, admin/users, admin/audit-log) and for the role-aware route
  guards described in spec FE-009/SEC-003.
- **Rationale**: Flagging this explicitly rather than folding it in silently, since it's a dependency not named
  verbatim in the approved decisions: a multi-page SPA needs *some* client-side routing mechanism, and React
  Router is the de facto standard pairing for React — the realistic alternative isn't "no router," it's
  "hand-roll an equivalent," which would be more code for no benefit. If you'd prefer a different router or a
  different pattern entirely, this is the one place in this plan worth a second look before implementation.
- **Alternatives considered**: TanStack Router — a newer, type-safe alternative; not chosen only to keep the
  dependency surface minimal and stick to the single most widely-documented option, not because of any concrete
  deficiency.

## Frontend test tooling

- **Decision**: Vitest (Vite-native test runner) + React Testing Library.
- **Rationale**: Vitest shares Vite's config/transform pipeline (no separate webpack/babel setup needed);
  React Testing Library is the standard choice for testing component behavior/accessibility rather than
  implementation details, matching spec FE-017's accessibility requirement.
- **Alternatives considered**: Jest — the older standard; rejected only because it requires separate
  configuration to work with Vite's build pipeline, which Vitest avoids entirely.
