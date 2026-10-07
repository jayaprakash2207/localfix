# Feature Specification: LocalFix Frontend and Web Authentication

**Feature Branch**: `002-web-frontend-auth`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Build the LocalFix web frontend (React/TypeScript/Vite/Tailwind) for the existing Feature 001
Authentication and RBAC backend, per the approved Feature 002 final proposal. Scope: public landing/login/registration/
forgot-password/reset-password; authenticated dashboard/profile/logout; Admin user management (search/filter/paginate/
role-change/enable-disable) and audit log; Citizen and Officer basic dashboards (identical structure). Backend support
required: a new cookie-establishing session endpoint (`POST /auth/session`) alongside the unchanged existing bearer-token
login endpoint; dual bearer/cookie session resolution; cookie clearing on logout; double-submit-cookie CSRF protection on
cookie-authenticated state-changing requests (bearer-authenticated requests exempt); a new Admin-only `GET /admin/users`
endpoint (search, role/status filters, pagination, safe fields only); real password-reset email delivery behind the
existing delivery seam; an explicit, required `COOKIE_SECURE` setting that fails closed in production; an explicit,
operator-configured `TRUSTED_PROXY_IPS` allow-list so the existing per-IP rate limiter keys on the real client address
behind a reverse proxy; CORS kept optional/off-by-default, restricted and non-wildcard if ever enabled. Development
runs through a same-origin Vite proxy; production runs frontend and backend under one origin via a reverse proxy — so
`SameSite=Lax` cookies work identically in both environments with no exception. All existing Feature 001 contracts,
security guarantees, and automated test coverage remain intact and unchanged except where this spec explicitly calls
for a new or changed contract. Out of scope: service requests, complaints, issue reporting, officer-assignment
workflow, notifications, maps, payments, mobile app, and any other LocalFix business functionality."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register and Log In via the Web Frontend (Priority: P1) 🎯 MVP

A resident visits the LocalFix site, creates an account, and logs in through the web UI. Their browser session is
established via a secure cookie; the raw session credential never becomes visible to frontend JavaScript. A
separate, already-existing way for non-browser API clients to log in (and receive a token directly) keeps working
exactly as it does today, unaffected by this change.

**Why this priority**: Nothing else in this feature is reachable without a working web login; preserving the
existing API contract is the hard constraint that makes everything else buildable without breaking Feature 001.

**Independent Test**: Register a new account through the web UI, log in through the web UI, and confirm a
protected web page loads using only the cookie (no token ever read from local storage or request bodies by the
frontend). Separately, confirm an existing non-browser client that logs in via the original bearer-token endpoint
and calls a protected endpoint with that token still succeeds, unchanged.

**Acceptance Scenarios**:

1. **Given** no existing account for a given email, **When** a resident completes the web registration form, **Then**
   the account is created (Citizen role, Active status) and the resident is taken to the login page.
2. **Given** a registered, Active account, **When** the resident submits correct credentials on the web login
   page, **Then** a session cookie is established and the resident lands on the authenticated dashboard, and at no
   point does the browser's JavaScript receive, store, or have access to the raw session credential.
3. **Given** a registered account, **When** the resident submits incorrect credentials on the web login page,
   **Then** a generic "invalid email or password" message is shown (status code `401`), with no indication of
   whether the account exists, is disabled, or is locked out.
4. **Given** an existing non-browser API client authenticating via the original bearer-token login endpoint
   exactly as it does under Feature 001, **When** it calls any protected endpoint with that token, **Then** the
   request succeeds exactly as it did before this feature existed — this endpoint's request and response shape
   are unchanged.
5. **Given** an email that is already registered, **When** a resident attempts to register again with that same
   email through the web UI, **Then** the web form shows a clear "already registered" message (status code
   `409`).
6. **Given** a resident submits a password shorter or longer than the existing password-length policy allows,
   **When** the web form is submitted, **Then** the web UI shows a clear validation message (status code `422`)
   without a round trip appearing to "hang" or fail silently.

---

### User Story 2 - View Dashboard and Profile, Log Out (Priority: P1)

Once logged in, any user (any role) can see a dashboard, view their own profile (email, role, account status,
creation date), and log out — ending the session on both the browser and the server.

**Why this priority**: The minimum authenticated experience every role needs, and the mechanism (session end)
that proves the cookie-based session is genuinely revocable, not just expirable.

**Independent Test**: Log in, view the dashboard and profile, log out, and confirm the now-logged-out browser can
no longer reach the dashboard or profile without logging in again.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they open their profile, **Then** they see their own email, role, account
   status, and creation date, and no information belonging to any other user.
2. **Given** a logged-in user, **When** they log out, **Then** their session cookie is cleared from the browser
   **and** the underlying server-side session is revoked, so neither the cookie nor any previously-observed
   session value can be reused afterward.
3. **Given** a session that has naturally expired without an explicit logout, **When** the user next tries to use
   the dashboard, **Then** they are treated exactly as a logged-out user and returned to the login page (status
   code `401` from the underlying request).

---

### User Story 3 - Backend-Enforced Role-Based Navigation (Priority: P1)

Citizens, Officers, and Admins each see navigation and actions appropriate to their role. This is a usability
convenience only — every underlying action is independently re-checked and enforced by the backend regardless of
what the frontend displays or allows a user to click.

**Why this priority**: This is the core security property the entire feature must preserve; it is not optional
polish.

**Independent Test**: Log in as each role and confirm the navigation differs as expected; separately, issue a
direct request for an action outside that role's visible navigation and confirm the backend rejects it
identically to how it already does under Feature 001, regardless of what the frontend would have allowed.

**Acceptance Scenarios**:

1. **Given** a logged-in Citizen or Officer, **When** they view the navigation, **Then** no Admin-only action
   (user management, audit log) is presented.
2. **Given** a logged-in Admin, **When** they view the navigation, **Then** Admin-only actions are presented in
   addition to the common dashboard/profile.
3. **Given** a logged-in Citizen, **When** a request for an Admin-only action is made directly (bypassing the
   UI entirely), **Then** the backend rejects it (status code `403`) exactly as it already does under Feature
   001 — the frontend's navigation choices have no bearing on this outcome.
4. **Given** any authenticated user receiving a `403` response from an attempted action, **When** the frontend
   handles that response, **Then** it shows an explicit "you don't have permission for this" message and does
   **not** log the user out (a `403` means the session is fine; the role isn't permitted — a different situation
   than a `401`).

---

### User Story 4 - CSRF-Protected State-Changing Requests (Priority: P1)

Every state-changing request made under the cookie-based web session includes an anti-CSRF token the frontend
automatically attaches; the backend rejects any such request where the token is missing or doesn't match. Requests
authenticated via the existing bearer-token mechanism are unaffected by this check.

**Why this priority**: Moving to cookie-based sessions reintroduces a cross-site request forgery risk that
bearer-token sessions never had; this must close before any cookie-authenticated mutation ships.

**Independent Test**: Perform a cookie-authenticated state-changing request (e.g., logout) with a missing or
mismatched anti-CSRF token and confirm it is rejected; perform the same category of request with a valid token and
confirm it succeeds; separately, perform an equivalent bearer-token-authenticated request with no anti-CSRF token
at all and confirm it still succeeds, proving the exemption is correctly scoped.

**Acceptance Scenarios**:

1. **Given** a cookie-authenticated web session, **When** the frontend issues a state-changing request (logout,
   an Admin role change, an Admin status change), **Then** the matching anti-CSRF token is attached
   automatically, with no user action required.
2. **Given** a cookie-authenticated session, **When** a state-changing request arrives with a missing or
   mismatched anti-CSRF token, **Then** the request is rejected (status code `403`).
3. **Given** a request authenticated via the existing bearer-token mechanism instead of a cookie, **When** a
   state-changing request is made with no anti-CSRF token present at all, **Then** the request still succeeds —
   the anti-CSRF requirement applies only to cookie-authenticated requests.

---

### User Story 5 - Admin Searches, Filters, and Paginates the User List (Priority: P2)

An Admin can find a specific user among all registered accounts by searching on email and filtering by role and
account status, browsing results a page at a time.

**Why this priority**: Without this, the Admin role-change and enable/disable capabilities (User Story 6) have no
way to find a target user through the UI at all — this is the enabling capability for all Admin user-management
actions.

**Independent Test**: As Admin, search for a known user by (partial) email, filter by role and by status, and
page through results; confirm no password, session, or reset-token data is ever present in what's returned.

**Acceptance Scenarios**:

1. **Given** multiple registered accounts, **When** an Admin searches by a partial, case-insensitive email match,
   **Then** only matching accounts are returned, with only their safe public fields (identifier, email, role,
   status, creation date).
2. **Given** a search or filter combination that matches no accounts, **When** the Admin views the results,
   **Then** the UI shows an explicit empty state, not an error and not an indefinitely blank list.
3. **Given** more accounts exist than fit on one page, **When** the Admin pages through results, **Then** each
   page shows the correct subset along with the total count, current page, and page size.
4. **Given** an out-of-bounds or invalid pagination or filter parameter, **When** the request is made, **Then**
   it is rejected with a clear validation error (status code `422`).
5. **Given** a non-Admin user, **When** they attempt to reach the user list (directly, bypassing the UI),
   **Then** the request is rejected (status code `403`).

---

### User Story 6 - Admin Changes Roles and Enables/Disables Accounts via the Web UI (Priority: P2)

Having found a user (User Story 5), an Admin can change that user's role or enable/disable their account directly
from the web UI, with the same invariants Feature 001 already enforces (no self-targeting, the last Active Admin
can never be removed) surfaced clearly when they apply.

**Why this priority**: This is the actual "do something" half of Admin user management; search alone has no value
without it.

**Independent Test**: As Admin, change another user's role and status and confirm both take effect; attempt to
change your own role/status and confirm it's rejected with a clear explanation; attempt to remove the last Active
Admin's role/status and confirm it's rejected with a clear explanation.

**Acceptance Scenarios**:

1. **Given** an Admin viewing another user's details, **When** they change that user's role or enable/disable
   their account, **Then** the change takes effect and is reflected immediately in the user list.
2. **Given** an Admin viewing their own account in the user list, **When** they attempt to change their own role
   or disable their own account, **Then** the action is rejected (status code `403`) and the UI explains why
   rather than showing a generic failure.
3. **Given** exactly one Active Admin remains, **When** any request would remove that account's Admin role or
   disable it, **Then** the action is rejected (status code `409`) and the UI explains why.

---

### User Story 7 - Admin Views and Filters the Audit Log via the Web UI (Priority: P2)

An Admin can browse the existing security audit trail through the web UI, filtering by affected user, action
type, and time range.

**Why this priority**: Completes the Admin capability set; depends on nothing else being built first, but ranks
below the ability to actually act on a user (Stories 5-6).

**Independent Test**: As Admin, perform a role change and a status change, then find both corresponding entries
in the audit log view using the available filters.

**Acceptance Scenarios**:

1. **Given** security-relevant actions have occurred, **When** an Admin opens the audit log, **Then** entries are
   shown with actor, action, affected user, and timestamp, and never any password or secret value.
2. **Given** a large audit history, **When** an Admin filters by affected user, action type, or a time range,
   **Then** only matching entries are shown.
3. **Given** a non-Admin user, **When** they attempt to reach the audit log (directly, bypassing the UI),
   **Then** the request is rejected (status code `403`).

---

### User Story 8 - Request and Complete Password Reset via Real Email (Priority: P2)

A user who forgot their password requests a reset through the web UI, receives an actual email containing a
single-use link, and sets a new password by following it — a fully usable, real end-to-end flow, not a
development workaround.

**Why this priority**: Feature 001 already has the reset *logic*; without real delivery, the web flow is not
actually usable by a real person — this closes that gap.

**Independent Test**: Request a reset for a real test-reachable email address, retrieve the delivered message,
follow its link into the reset-confirm page, submit a new password, and log in with it.

**Acceptance Scenarios**:

1. **Given** a registered email, **When** the resident submits the "forgot password" form, **Then** a real email
   is dispatched containing a single-use, time-limited reset link, and the web UI shows a generic confirmation
   that does not reveal whether the email was actually registered.
2. **Given** an email that is not registered, **When** the same form is submitted, **Then** the identical generic
   confirmation is shown and no email is sent — this matches Feature 001's existing non-disclosure behavior.
3. **Given** a valid, unexpired reset link, **When** the resident follows it and submits a new password meeting
   the existing password policy, **Then** the password is updated and they can log in with it; the old password
   stops working.
4. **Given** an expired or already-used reset link, **When** the resident attempts to use it, **Then** the web UI
   shows a clear, specific error (status code `400`) rather than a generic failure.
5. **Given** any point in this flow, **When** the reset token exists in transit or at rest, **Then** it is never
   shown in any frontend UI element and never written to any log output.

---

### User Story 9 - Citizen and Officer Basic Dashboards (Priority: P3)

Citizens and Officers each see a basic dashboard and profile with their own account information. The two are
structurally identical for this feature — no role-specific business functionality exists yet for either.

**Why this priority**: Lowest-risk, most self-contained story; depends only on the common authenticated shell
(User Story 2).

**Independent Test**: Log in as a Citizen and as an Officer and confirm both see the same dashboard structure,
each showing their own (different) account information.

**Acceptance Scenarios**:

1. **Given** a logged-in Citizen, **When** they view their dashboard, **Then** they see their own profile and
   account information and no Admin-only or Officer-specific functionality (none exists).
2. **Given** a logged-in Officer, **When** they view their dashboard, **Then** the structure is identical to a
   Citizen's dashboard, showing their own (different) account information.

---

### User Story 10 - Correct Rate Limiting Behind a Reverse Proxy (Priority: P3)

In production, where the frontend and backend sit behind a reverse proxy, the existing per-source-IP rate limits
on registration and password-reset-request continue to apply based on each real visitor's own address, not the
proxy's shared address — and the system never honors a forwarded-address claim from a source it hasn't explicitly
been configured to trust.

**Why this priority**: A deployment-architecture correctness requirement rather than a user-facing flow; it must
hold before production launch but doesn't block earlier stories' development or testing.

**Independent Test**: Simulate requests arriving through a configured trusted-proxy address carrying different
forwarded client addresses, and confirm the rate limiter tracks each forwarded address separately; separately,
simulate a forwarded-address header arriving from a source that is *not* in the trusted configuration and confirm
it is ignored (the connecting address is used instead).

**Acceptance Scenarios**:

1. **Given** a request arrives via a connecting address that is in the configured trusted-proxy list, carrying a
   forwarded client address, **When** the rate limiter evaluates the request, **Then** it keys on the forwarded
   client address, not the proxy's own address.
2. **Given** a request arrives via a connecting address that is **not** in the configured trusted-proxy list,
   carrying a forwarded-address header, **When** the rate limiter evaluates the request, **Then** the forwarded
   header is ignored entirely and the direct connecting address is used instead.
3. **Given** no trusted-proxy configuration exists at all, **When** any request is evaluated, **Then** the
   system behaves exactly as it does today (direct connecting address only) — this is the safe default.
4. **Given** the existing 5-requests-per-15-minutes limit, **When** it is exceeded by a real client identified
   correctly per the above, **Then** that specific client (and no other) receives `429` on the 6th+ request.

---

### User Story 11 - Cookie Security Configuration Fails Closed in Production (Priority: P3)

The session cookie's security posture is explicit, required configuration — never an implicit or forgotten
default — and a production configuration that would result in an insecure cookie refuses to start at all rather
than silently running insecurely.

**Why this priority**: A deployment-safety guard, not a user-facing flow; important before any real production
launch, independent of the other stories' development.

**Independent Test**: Attempt to start the system configured for a production environment with the cookie
security setting set to an insecure value, and confirm it refuses to start; confirm a development configuration
with the insecure value starts normally; confirm a production configuration with the secure value starts
normally.

**Acceptance Scenarios**:

1. **Given** a development environment configuration with the cookie security setting explicitly set to
   insecure, **When** the system starts, **Then** it starts normally (matching plain local HTTP development).
2. **Given** a production environment configuration with the cookie security setting explicitly set to secure,
   **When** the system starts, **Then** it starts normally.
3. **Given** a production environment configuration with the cookie security setting explicitly set to
   insecure, **When** the system attempts to start, **Then** it refuses to start with a clear configuration
   error, rather than running with an insecure cookie.
4. **Given** the cookie security setting is left entirely unset, **When** the system attempts to start in any
   environment, **Then** it refuses to start rather than silently assuming a value — this setting has no
   implicit default.

---

### Edge Cases

- What happens when neither a bearer token nor a session cookie is present on a protected request? (Rejected,
  status code `401`, identical to today's Feature 001 behavior.)
- What happens when a cookie session has expired but its paired anti-CSRF cookie is still present in the browser?
  (Authentication fails first with `401`; the CSRF check never runs, since there is no valid session to protect.)
- What happens when an unauthenticated user directly navigates to an Admin-only frontend page? (The frontend
  redirects to login as a UX convenience; independently, any underlying request that page would have made is
  rejected by the backend with `401` or `403` regardless of whether the frontend redirect happens correctly.)
- What happens when the registration or password-reset-request rate limit is exceeded? (`429`, with a specific
  "too many attempts" message, not a generic error — see User Story 1 and User Story 8.)
- What happens when a password-reset link has expired or was already used? (`400`, with a specific message — see
  User Story 8, Acceptance Scenario 4.)
- What happens when a duplicate email is submitted at registration? (`409`, surfaced clearly in the web form —
  see User Story 1, Acceptance Scenario 5.)
- What happens when an Admin attempts to change their own role or disable their own account via the UI? (Rejected
  with `403` and an explicit reason — see User Story 6, Acceptance Scenario 2.)
- What happens when a role or status change targets the last remaining Active Admin? (Rejected with `409` and an
  explicit reason — see User Story 6, Acceptance Scenario 3.)
- What happens if cross-origin access is never enabled at all (the default posture for both the development and
  production architectures this feature assumes)? (No cross-origin requests are possible; this is the intended
  default, not a gap — see Assumptions.)
- What happens when a forwarded client-address header arrives from a connecting address that was never configured
  as a trusted proxy? (Ignored entirely — see User Story 10, Acceptance Scenario 2.)

## Requirements *(mandatory)*

### Frontend Functional Requirements

- **FE-001**: System MUST provide a public landing page.
- **FE-002**: System MUST provide a registration page that surfaces field-level validation and duplicate-email
  errors returned by the backend.
- **FE-003**: System MUST provide a login page that establishes a cookie-based session without the raw session
  credential ever becoming accessible to frontend JavaScript or being written to any browser storage the
  frontend controls.
- **FE-004**: System MUST provide a logout action that ends the current session, on both the browser (clearing
  the session cookie) and the server (revoking the underlying session).
- **FE-005**: System MUST provide a "forgot password" page whose confirmation message is identical regardless of
  whether the submitted email is registered.
- **FE-006**: System MUST provide a "reset password" page that reads the reset token from the link the user
  arrived on and submits a new password meeting the existing password-length policy.
- **FE-007**: System MUST provide an authenticated dashboard shell available to any logged-in user regardless of
  role.
- **FE-008**: System MUST provide a profile view showing only the current user's own email, role, account
  status, and creation date.
- **FE-009**: System MUST adapt visible navigation and actions to the current user's role (Citizen/Officer/Admin)
  as a usability convenience; this adaptation MUST NOT be relied upon as an authorization mechanism (see
  SEC-003).
- **FE-010**: System MUST provide an Admin-only user management view supporting search by email, filtering by
  role and by account status, and page-based pagination.
- **FE-011**: System MUST provide an Admin-only control to change a target user's role, displaying the specific
  backend-provided reason when a self-targeted or last-admin-violating change is rejected.
- **FE-012**: System MUST provide an Admin-only control to enable/disable a target user's account, displaying the
  specific backend-provided reason when a self-targeted or last-admin-violating change is rejected.
- **FE-013**: System MUST provide an Admin-only audit log view supporting filtering by affected user, action
  type, and time range.
- **FE-014**: System MUST provide a basic dashboard for Citizen and Officer users, structurally identical between
  the two roles, showing only profile and account information.
- **FE-015**: Every view that depends on a network request MUST present a distinct loading state, error state,
  and (for list views) empty state — never an indefinite blank screen.
- **FE-016**: The layout MUST remain usable, without horizontal scrolling or inaccessible controls, at both a
  mobile-width and a desktop-width viewport.
- **FE-017**: Interactive forms and controls MUST be operable via keyboard and expose accessible names/labels to
  assistive technology.
- **FE-018**: Upon receiving a `401` response during normal authenticated use, the frontend MUST clear local
  session state and route the user to the login page.
- **FE-019**: Upon receiving a `403` response, the frontend MUST present an explicit "not permitted" message
  without clearing local session state or logging the user out.
- **FE-020**: Upon receiving a `429` response on registration or password-reset-request, the frontend MUST
  present a specific "too many attempts, try again later" message rather than a generic error.
- **FE-021**: The frontend MUST attach the anti-CSRF token to every state-changing request made under the
  cookie-based session automatically, requiring no user action.

### Backend Functional Requirements

- **BE-001**: System MUST provide a session-establishing endpoint for the web frontend that sets an HttpOnly
  session cookie and does not return the raw session credential in the response body.
- **BE-002**: System MUST continue to support the existing bearer-token login endpoint with its exact current
  request and response contract, unchanged, for non-browser clients.
- **BE-003**: System MUST authenticate a request using EITHER a valid `Authorization` bearer credential OR a
  valid session cookie, checking the bearer credential first so that behavior for any client already sending one
  is completely unchanged.
- **BE-004**: System MUST clear the session cookie when a cookie-authenticated session logs out, in addition to
  the existing server-side session revocation (FR-006 from Feature 001).
- **BE-005**: System MUST issue an anti-CSRF token alongside the session cookie at web login, in a form readable
  by frontend JavaScript (unlike the session cookie itself).
- **BE-006**: System MUST require a matching anti-CSRF token on every cookie-authenticated state-changing
  request (at minimum: logout, role change, account status change, and any future one), rejecting a request with
  a missing or mismatched token.
- **BE-007**: System MUST NOT require an anti-CSRF token on a request authenticated via the bearer credential.
- **BE-008**: System MUST provide an Admin-only endpoint to list user accounts, supporting search by (partial,
  case-insensitive) email, filtering by role, filtering by account status, and page-based pagination with a
  total count, current page, and page size in the response.
- **BE-009**: The user-listing endpoint MUST return only the same safe public fields used elsewhere in the system
  (identifier, email, role, status, creation date) and MUST NEVER return password, password-hash, session-token,
  or reset-token data.
- **BE-010**: System MUST deliver password-reset emails through a real delivery mechanism, preserving the
  existing single-use, time-limited reset-link behavior unchanged.
- **BE-011**: System MUST NEVER display or log the raw password-reset token at any point in the delivery
  mechanism or anywhere else.
- **BE-012**: System MUST require an explicit configuration value controlling whether the session cookie is
  marked Secure, with no implicit default value.
- **BE-013**: System MUST refuse to start when configured for a production environment while the cookie-security
  configuration value is set to an insecure value.
- **BE-014**: System MUST support an explicit, operator-configured list of trusted reverse-proxy addresses, and
  MUST only honor forwarded client-address information when the immediately connecting peer is in that
  configured list.
- **BE-015**: When no trusted-proxy configuration is present, the system MUST continue to use the direct
  connecting peer's address for rate-limiting purposes, exactly as it does today.
- **BE-016**: The existing per-source-address rate limits on registration and password-reset-request (5 requests
  per 15 minutes, per Feature 001 FR-030) MUST continue to apply, keyed on the correct real client address once
  trusted-proxy configuration is in effect.
- **BE-017**: IF cross-origin access is ever enabled for local development, it MUST be restricted to an explicit,
  statically configured set of allowed origins, MUST NOT combine a wildcard origin with credentials, and MUST
  NOT reflect an arbitrary request origin back to the caller.

### Security & Non-Functional Requirements

- **SEC-001**: The browser-based session mechanism MUST NOT expose the raw session credential to any
  frontend-executable code at any point in the normal web login flow.
- **SEC-002**: All existing Feature 001 authorization, session-validity, account-status, password-policy,
  brute-force-lockout, last-admin-invariant, and audit-logging guarantees MUST remain enforced exactly as before,
  independent of whether a given request's session was established via bearer credential or cookie.
- **SEC-003**: Role-based navigation and UI-hiding in the frontend is a usability aid only; the backend MUST
  independently enforce every authorization decision regardless of what the frontend displays or allows a user to
  attempt.
- **SEC-004**: The anti-CSRF requirement MUST apply uniformly to every cookie-authenticated state-changing
  request, with no endpoint-specific exception, and MUST NOT apply to bearer-authenticated requests.
- **SEC-005**: The system MUST NOT trust a forwarded client-address header from any source other than an
  explicitly configured trusted-proxy address.
- **SEC-006**: Production deployment MUST NOT be able to silently start with an insecure cookie configuration.

### Key Entities

- **Web Session**: The cookie-based representation of an existing Feature 001 session for a browser client. Not a
  new stored entity — the same underlying session record Feature 001 already tracks, reached via a cookie instead
  of (or in addition to) a bearer credential.
- **Anti-CSRF Token**: A value issued alongside a Web Session, readable by frontend JavaScript, that must be
  echoed back on cookie-authenticated state-changing requests. Tied to the Web Session it was issued with.
- **User List Query**: The shape of an Admin's search/filter/pagination request against the user-listing
  capability (search text, role filter, status filter, page, page size) and its corresponding result (matching
  users' safe public fields, total count, current page, page size).
- **Trusted Proxy Configuration**: Operator-provided configuration (not end-user data) listing which reverse-proxy
  addresses the system will accept forwarded client-address information from.
- **Cookie Security Configuration**: Operator-provided, required (no default) configuration controlling whether
  the session cookie is marked Secure, validated against the deployment environment at startup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of web registration, login, dashboard, profile, and logout actions complete in automated
  testing without the raw session credential ever being observable to frontend-executable code.
- **SC-002**: 100% of Feature 001's existing automated test coverage for the bearer-token login contract
  continues to pass unmodified, with zero regressions introduced by this feature.
- **SC-003**: 100% of cookie-authenticated state-changing requests made without a valid anti-CSRF token are
  rejected in testing; 100% of equivalent bearer-authenticated requests succeed without one.
- **SC-004**: An Admin can locate a specific user via search and complete a role or status change for them in
  under one minute under normal conditions.
- **SC-005**: 100% of requests simulated as arriving through a configured trusted-proxy address are rate-limited
  according to their real forwarded client address, not the proxy's own address, in testing; 100% of requests
  carrying a forwarded-address header from an untrusted source have that header ignored.
- **SC-006**: 100% of attempts to start the system with a production environment configuration and an insecure
  cookie-security value are refused in testing; 100% of attempts to start with the cookie-security value entirely
  unset are refused in testing, in any environment.
- **SC-007**: 100% of password-reset requests in testing result in an actual dispatched email via a real delivery
  mechanism, with the raw reset token never appearing in any UI surface or log output.
- **SC-008**: 100% of backend authorization decisions remain correct in testing even when a request bypasses the
  frontend's navigation entirely and attempts an action outside the current user's role.
- **SC-009**: Every list and detail view in scope presents a distinct loading, error, or empty state in testing —
  none present an indefinite blank screen.
- **SC-010**: Every screen in scope remains fully usable, with no horizontal scrolling and no inaccessible
  controls, at both a mobile-width and a desktop-width viewport.

## Assumptions

- Feature 001's existing backend behavior, data model, and automated test coverage are treated as a fixed,
  already-shipped contract; nothing in Feature 001 changes except the specific new/changed capabilities this
  specification names (the new session-establishing endpoint, dual bearer/cookie resolution, cookie-clearing on
  logout, anti-CSRF protection, the new user-listing endpoint, real email delivery, the explicit cookie-security
  setting, and trusted-proxy configuration).
- "Real email delivery" means an actual message is dispatched through a genuine delivery mechanism in each
  environment; the specific provider is an implementation/planning decision, not a specification concern.
- Cross-origin access (CORS) is an optional, off-by-default capability reserved for a possible future API
  consumer; the development architecture (same-origin via a local development proxy) and the production
  architecture (same-origin via a reverse proxy) described by this feature do not require it to be enabled.
- The new session-establishing endpoint and the trusted-proxy configuration value use the names already agreed
  upon (`POST /auth/session`, `TRUSTED_PROXY_IPS`) unless a concrete specification-level reason to deviate
  emerges during planning.
- "Mobile and desktop" usability is interpreted against standard common viewport breakpoints (roughly
  phone-width and roughly laptop/desktop-width); no specific device matrix is mandated.
- Admin user-list pagination defaults to a sensible minimum page size and a capped maximum page size, with exact
  numeric bounds left to planning rather than fixed here, since the specific values do not change the feature's
  scope or user experience.
- Citizen and Officer dashboards are intentionally identical in structure for this feature; any future
  role-specific business functionality for either is explicitly out of scope here (see Out of Scope).

## Out of Scope

- Service requests, complaints, and issue reporting.
- Officer-assignment workflow.
- Notifications.
- Maps.
- Payments.
- A mobile application.
- Any other LocalFix business functionality beyond authentication, RBAC, and the Admin/Citizen/Officer
  capabilities explicitly listed in this specification's User Scenarios.
