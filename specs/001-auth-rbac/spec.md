# Feature Specification: Authentication and Role-Based Access Control

**Feature Branch**: `001-auth-rbac`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Create Feature 001: Authentication and Role-Based Access Control for LocalFix. LocalFix has three roles: Citizen, Officer, Admin. The authentication system must allow users to register, login, logout, view their own profile, reset their password. New users must automatically receive the Citizen role. Users must not be able to select or assign themselves the Officer or Admin role. Citizens can access citizen functionality. Officers can access officer functionality. Admins can access administrative functionality. The backend must enforce authorization. The frontend must not be considered a security boundary. Users must not be able to access another user's protected information. Passwords must never be stored as plaintext and must never appear in API responses or logs. User accounts have ACTIVE and DISABLED states. Disabled users cannot authenticate. The system must protect login against brute-force attempts and authenticated sessions must expire. Important authentication and account-security actions should be auditable. The feature must include automated tests for authentication, authorization, role protection, account status, and important security rules."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Citizen Registration and First Login (Priority: P1)

A new resident creates a LocalFix account and is immediately able to log in and use citizen-facing functionality, without any ability to grant themselves elevated access.

**Why this priority**: Registration and login are the entry point for every other capability in the system. Without this, no other story is reachable.

**Independent Test**: Can be fully tested by registering a new account, confirming it is created with the Citizen role, and logging in with the new credentials to reach citizen functionality.

**Acceptance Scenarios**:

1. **Given** no existing account for a given email, **When** a person submits valid registration details, **Then** a new account is created with the Citizen role and ACTIVE status.
2. **Given** a registration request that includes a role field (e.g., Officer or Admin), **When** the account is created, **Then** the system ignores/rejects the supplied role and the account still receives the Citizen role only.
3. **Given** a newly registered, ACTIVE account, **When** the user logs in with correct credentials, **Then** the user is authenticated and granted access to citizen functionality only.
4. **Given** an email that is already registered, **When** a person attempts to register with that same email, **Then** registration is rejected without revealing which account field caused the conflict beyond "already registered."

---

### User Story 2a - Admin Role Assignment (Priority: P1)

An Admin can promote an existing Citizen (or Officer) account to Officer or Admin, since no user can grant themselves elevated access.

**Why this priority**: Without an in-scope way to create Officer/Admin accounts, those roles can never be populated and User Story 2's officer/admin paths are untestable.

**Independent Test**: Can be fully tested by having an authenticated Admin change another user's role and confirming the target account's permitted functionality changes accordingly on their next authenticated action.

**Acceptance Scenarios**:

1. **Given** an authenticated Admin, **When** they assign the Officer or Admin role to an existing user account, **Then** that account's role is updated and an audit record is created for the role change.
2. **Given** an authenticated Citizen or Officer (non-Admin), **When** they attempt to change any account's role, **Then** the request is denied by the backend.
3. **Given** a role change takes effect, **When** the affected user next authenticates or is authorization-checked, **Then** the system enforces the new role rather than the old one.
4. **Given** an authenticated Admin attempting to change their own role away from Admin, **When** the request is submitted, **Then** it is denied.
5. **Given** exactly one ACTIVE Admin account remains in the system, **When** any request would change that account's role away from Admin, **Then** it is denied so that at least one ACTIVE Admin always remains.

---

### User Story 2b - Admin Account Status Management (Priority: P2)

An Admin can enable or disable any user account, but no user — including an Admin — can disable their own account, and the system never ends up with zero ACTIVE Admin accounts.

**Why this priority**: Account disablement (User Story 6) is only trustworthy if the authority to trigger it is itself tightly controlled; this closes that gap.

**Independent Test**: Can be fully tested by having an Admin disable/enable another account, confirming a non-Admin cannot do so, confirming a user cannot disable their own account, and confirming the system blocks an action that would remove the last ACTIVE Admin.

**Acceptance Scenarios**:

1. **Given** an authenticated Admin, **When** they disable or enable another user's account, **Then** the status change takes effect and an audit record is created.
2. **Given** an authenticated Citizen or Officer (non-Admin), **When** they attempt to change any account's status, **Then** the request is denied by the backend.
3. **Given** any authenticated user, **When** they attempt to disable their own account, **Then** the request is denied, regardless of role.
4. **Given** exactly one ACTIVE Admin account remains in the system, **When** any request would disable that account, **Then** it is denied so that at least one ACTIVE Admin always remains.

---

### User Story 2 - Role-Based Access Enforcement (Priority: P1)

Citizens, Officers, and Admins each reach only the functionality permitted for their role, and the backend blocks any attempt to reach functionality outside that role even if the frontend would have allowed the attempt.

**Why this priority**: Role separation is the core security guarantee of this feature; without enforced backend checks, every other control is cosmetic.

**Independent Test**: Can be fully tested by authenticating as each role and attempting to call citizen-only, officer-only, and admin-only operations, confirming only permitted calls succeed regardless of what the client sends.

**Acceptance Scenarios**:

1. **Given** an authenticated Citizen, **When** they call citizen functionality, **Then** the request succeeds.
2. **Given** an authenticated Citizen, **When** they call officer-only or admin-only functionality (directly, bypassing the UI), **Then** the backend rejects the request with an authorization error.
3. **Given** an authenticated Officer, **When** they call officer functionality, **Then** the request succeeds; **When** they call admin-only functionality, **Then** the backend rejects the request.
4. **Given** an authenticated Admin, **When** they call administrative functionality, **Then** the request succeeds.
5. **Given** any authenticated user, **When** a protected request arrives without passing through the official client (e.g., a direct API call), **Then** the backend still enforces the same role check as if the request came from the normal interface.

---

### User Story 3 - Protecting Other Users' Information (Priority: P1)

A user can see and manage only their own protected information; they cannot view or infer another user's protected account information by any means exposed by the system.

**Why this priority**: Cross-user data exposure is a critical privacy failure and must hold from the first release.

**Independent Test**: Can be fully tested by authenticating as User A and attempting to retrieve User B's profile or account data (including by guessing/incrementing identifiers), confirming every such attempt is denied.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request their own profile, **Then** their own data is returned.
2. **Given** an authenticated user, **When** they request another user's profile or protected account data by any identifier, **Then** the request is denied.
3. **Given** an authenticated user, **When** they attempt to modify another user's account state or credentials, **Then** the request is denied.

---

### User Story 4 - Logout and Session Expiration (Priority: P2)

A user can end their session on demand, and any session that is not explicitly ended still stops working after it expires.

**Why this priority**: Session termination (voluntary and automatic) limits the window in which a stolen or forgotten session can be abused.

**Independent Test**: Can be fully tested by logging in, logging out, and confirming the prior session can no longer access protected functionality; separately, by confirming an idle/expired session is also rejected.

**Acceptance Scenarios**:

1. **Given** an authenticated session, **When** the user logs out, **Then** that session can no longer be used to access protected functionality.
2. **Given** an authenticated session that has exceeded its expiration, **When** it is used to access protected functionality, **Then** the request is denied and the user must re-authenticate.

---

### User Story 5 - Password Reset (Priority: P2)

A user who cannot log in because they forgot their password can regain access to their account through a self-service reset process without needing to know their old password.

**Why this priority**: Password recovery is essential to usable account ownership, but the system is still usable without it for a short initial period, so it ranks below core auth/authorization guarantees.

**Independent Test**: Can be fully tested by requesting a password reset for a known account, completing the reset through whatever verification step is defined, and confirming login succeeds with the new password and fails with the old one.

**Acceptance Scenarios**:

1. **Given** an ACTIVE account, **When** the owner requests a password reset, **Then** the system sends a single-use, time-limited reset link to the account's registered email.
2. **Given** a valid, unexpired reset link, **When** the owner follows it and submits a new password, **Then** the password is updated and they can subsequently log in with it.
3. **Given** a completed password reset, **When** the user attempts to log in with the old password, **Then** authentication fails.
4. **Given** a password reset request for an email that is not registered, **When** the request is submitted, **Then** the system responds the same way as for a registered email (no account-existence disclosure), and no email is sent.
5. **Given** a reset link that has expired or was already used, **When** it is submitted, **Then** the reset is rejected and the password remains unchanged.

---

### User Story 6 - Account Disablement Enforcement (Priority: P2)

A DISABLED account cannot be used to authenticate or access any protected functionality, even with correct credentials.

**Why this priority**: Disablement is the primary lever an Admin has to immediately cut off a problematic or compromised account, so it must be reliable.

**Independent Test**: Can be fully tested by disabling an account and confirming that correct-credential login attempts, and any existing sessions, are rejected.

**Acceptance Scenarios**:

1. **Given** a DISABLED account, **When** the owner attempts to log in with correct credentials, **Then** authentication is denied.
2. **Given** an account that is disabled while a session is already active, **When** that session is next used, **Then** access is denied.

---

### User Story 7 - Brute-Force Login Protection (Priority: P2)

Repeated failed login attempts against an account or from a source are detected and throttled or blocked, so password guessing is impractical.

**Why this priority**: Without this, the strength of password storage and role checks can be undermined by simple credential-guessing attacks.

**Independent Test**: Can be fully tested by submitting repeated incorrect login attempts and confirming that further attempts are throttled or blocked before an unlimited number of guesses is possible.

**Acceptance Scenarios**:

1. **Given** 5 consecutive failed login attempts for the same account within a short period, **When** the 5th failure occurs, **Then** the account is locked out for a fixed 15-minute cool-down period, during which further login attempts for that account are rejected regardless of credential correctness.
2. **Given** a locked-out account, **When** the 15-minute cool-down elapses, **Then** the legitimate owner can authenticate again with correct credentials.
3. **Given** a successful login, **When** it occurs, **Then** the account's consecutive failed-attempt count resets to zero.

---

### User Story 8 - Security Audit Trail (Priority: P3)

Security-sensitive authentication and account actions are recorded so that they can be reviewed after the fact.

**Why this priority**: Auditability supports accountability and incident investigation but does not block day-one usability of the feature.

**Independent Test**: Can be fully tested by performing security-sensitive actions (register, login success/failure, logout, password reset, role change, enable/disable) and confirming each produces a corresponding audit record.

**Acceptance Scenarios**:

1. **Given** a security-sensitive action occurs (e.g., login success, login failure, logout, password reset, account enable/disable, role change), **When** it completes, **Then** an audit record is created identifying the actor, the action, the affected resource, and the timestamp.
2. **Given** an audit record, **When** it is inspected, **Then** it contains no plaintext password or secret value.

---

### Edge Cases

- What happens when a registration payload includes an unexpected or forged role, status, or identifier field? (System must ignore/reject client-supplied privileged fields and apply server-determined defaults.)
- What happens when a user attempts to access a protected resource using a modified/guessed identifier belonging to another user?
- What happens when a disabled account's existing session is reused before the session would have naturally expired?
- What happens when a password reset is requested for an email that does not exist in the system? (Response must not disclose whether the email is registered, and no email is sent.)
- What happens when a password reset link is used a second time after already being consumed? (Must be rejected as expired/invalid.)
- What happens when a new password reset is requested while a prior one is still outstanding? (The prior reset link should be invalidated so only the newest one works.)
- What happens when login attempts fail repeatedly across many different accounts from the same source, rather than many attempts against one account? (Out of scope for per-account lockout; not addressed by this feature.)
- How does the system respond when an already-authenticated, non-expired session's underlying account is changed from ACTIVE to DISABLED?
- What happens when an Officer or Admin account is itself disabled (by another Admin)?
- What happens when an Admin attempts to change their own role away from Admin, or disable their own account? (Both MUST be rejected; see FR-004d and FR-019c.)
- What happens when a role change or account-disable action would leave zero ACTIVE Admin accounts? (Must be rejected to preserve at least one ACTIVE Admin; see FR-004e and FR-019d.)
- What happens when a non-Admin (Citizen or Officer) attempts to enable or disable any account, including their own? (Must be rejected; only Admin may change account status.)
- What happens when an Admin attempts to assign a role value outside Citizen/Officer/Admin? (Must be rejected.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a person to register a new account by supplying the required registration details (at minimum, a unique account identifier and a password).
- **FR-002**: System MUST automatically assign the Citizen role to every newly registered account.
- **FR-003**: System MUST ignore or reject any role value supplied by the client during registration; the client MUST NOT be able to cause an account to be created with the Officer or Admin role.
- **FR-004**: System MUST NOT expose any self-service mechanism by which an authenticated user can change their own role to Officer or Admin.
- **FR-004a**: System MUST allow an authenticated Admin to change any user account's role to Citizen, Officer, or Admin.
- **FR-004b**: System MUST reject any attempt by a non-Admin (Citizen or Officer) to change any account's role, including their own.
- **FR-004c**: System MUST reject role-change requests specifying a role value other than Citizen, Officer, or Admin.
- **FR-004d**: System MUST reject any attempt by an Admin to change their own role away from Admin.
- **FR-004e**: System MUST reject any role-change request that would result in zero ACTIVE accounts holding the Admin role; at least one ACTIVE Admin account MUST always remain.
- **FR-005**: System MUST allow a registered, ACTIVE user to log in by presenting valid credentials.
- **FR-006**: System MUST allow an authenticated user to log out, after which the session used for that login MUST no longer grant access to protected functionality.
- **FR-007**: System MUST allow an authenticated user to view their own profile information.
- **FR-008**: System MUST prevent any user, regardless of role, from viewing another user's protected profile or account information.
- **FR-009**: System MUST prevent any user, regardless of role, from modifying another user's account state or credentials, except where explicitly permitted by that user's role-granted administrative functionality.
- **FR-010**: System MUST allow a user to initiate a self-service password reset by requesting a single-use, time-limited link sent to the account's registered email, without needing their current password.
- **FR-010a**: System MUST invalidate a password reset link after it has been used once, after it expires, or when a newer reset link is issued for the same account (whichever comes first).
- **FR-010b**: System MUST respond identically to password reset requests regardless of whether the supplied email corresponds to a registered account, and MUST NOT send an email for an unregistered address.
- **FR-011**: System MUST enforce every authorization decision on the backend; the frontend MUST NOT be relied upon as a security boundary, and identical checks MUST apply whether a request originates from the official client or any other caller.
- **FR-012**: System MUST restrict citizen-designated functionality to users holding the Citizen role.
- **FR-013**: System MUST restrict officer-designated functionality to users holding the Officer role.
- **FR-014**: System MUST restrict administrative functionality to users holding the Admin role.
- **FR-015**: System MUST reject any request to functionality not permitted by the requester's role, without granting partial access.
- **FR-016**: System MUST store passwords only as the output of a one-way, salted cryptographic hash; the system MUST NOT persist passwords in plaintext or in a reversible form.
- **FR-017**: System MUST NOT include a user's password (plaintext or hashed) in any API response.
- **FR-018**: System MUST NOT write a user's password (plaintext or hashed) to any application, access, or audit log.
- **FR-019**: System MUST support ACTIVE and DISABLED states for every user account.
- **FR-020**: System MUST deny authentication for any account in the DISABLED state, even when the correct credentials are supplied, without disclosing whether the denial was due to disablement versus incorrect credentials.
- **FR-021**: System MUST deny continued use of any existing session belonging to an account that has transitioned to DISABLED.
- **FR-019a**: System MUST restrict changing a user account's status between ACTIVE and DISABLED to the Admin role.
- **FR-019b**: System MUST reject any attempt by a non-Admin (Citizen or Officer) to change any account's status.
- **FR-019c**: System MUST reject any attempt by a user, including an Admin, to disable their own account.
- **FR-019d**: System MUST reject any account-disable request that would result in zero ACTIVE accounts holding the Admin role; at least one ACTIVE Admin account MUST always remain.
- **FR-022**: System MUST lock out an account for 15 minutes after 5 consecutive failed login attempts against it, rejecting further login attempts for that account (regardless of credential correctness) until the cool-down elapses.
- **FR-022a**: System MUST reset an account's consecutive failed-attempt count to zero upon a successful login.
- **FR-023**: System MUST cause authenticated sessions to expire, after which the expired session MUST no longer grant access to protected functionality and the user MUST re-authenticate.
- **FR-024**: System MUST create an audit record for each security-sensitive authentication/account action, including at minimum: registration, login success, login failure, logout, password reset, account enable/disable, and role change.
- **FR-025**: Each audit record MUST identify the acting party (or "system"/"unauthenticated" where no authenticated actor exists), the action performed, the affected account/resource, and the timestamp of the action.
- **FR-026**: Audit records MUST NOT contain plaintext passwords, password hashes, or other credential secrets.
- **FR-027**: System MUST provide automated test coverage for: authentication (registration, login, logout), authorization (role-based access restrictions), role protection (inability to self-assign Officer/Admin), account status enforcement (ACTIVE/DISABLED behavior), and the security rules in this specification (password storage/exposure, brute-force protection, session expiration, auditability).
- **FR-028**: System MUST reject any password shorter than 8 characters or longer than 128 characters at registration and at password-reset confirmation. No additional forced complexity rules (e.g., required character classes) apply beyond this length bound.
- **FR-029**: System MUST treat email addresses as case-insensitive for both uniqueness enforcement and login lookup (e.g., `Alice@Example.com` and `alice@example.com` MUST refer to the same account, and the second registration attempt MUST be rejected as a duplicate).
- **FR-030**: System MUST rate-limit `POST /auth/register` and `POST /auth/password-reset/request` to 5 requests per 15 minutes per source IP address, enforced using the existing PostgreSQL-backed pattern already established for login lockout (FR-022) — no additional infrastructure (e.g., Redis) is introduced for this.
- **FR-031**: System MUST ensure that authentication-failure responses — including response timing, not only response body content — do not reveal whether a supplied email corresponds to a registered account. This strengthens FR-020's non-disclosure intent to explicitly cover timing side-channels.

### Key Entities

- **User Account**: Represents a registered person. Key attributes: unique identifier (e.g., email), hashed password, assigned role (Citizen, Officer, or Admin), account status (ACTIVE or DISABLED), profile information visible to the owner, timestamps for creation and last change.
- **Role**: One of exactly three values — Citizen, Officer, Admin — determining which functionality a User Account may access. Exactly one role is assigned per account at any time. The system MUST always have at least one ACTIVE User Account with the Admin role.
- **Session**: Represents an authenticated login instance tied to a single User Account. Key attributes: owning account, creation time, expiration time, current validity (active, logged out, or expired).
- **Password Reset Request**: Represents an in-progress, time-bounded, single-use request to replace a User Account's password, delivered as a link to the account's registered email. Key attributes: owning account, creation time, expiration time, used/unused status.
- **Login Attempt Record**: Tracks consecutive failed login attempts per account to drive lockout. Key attributes: owning account, consecutive failure count, lockout-until timestamp (if locked).
- **Audit Record**: Represents a logged security-sensitive event. Key attributes: acting party, action type, affected account/resource, timestamp, outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of registration attempts that supply a non-Citizen role are created with the Citizen role instead (i.e., zero accounts are ever created with a client-chosen Officer or Admin role).
- **SC-002**: 100% of requests to functionality outside a user's role are denied by the backend in testing, including requests that bypass the normal client interface entirely.
- **SC-003**: 0 occurrences of plaintext or hashed passwords found in API responses or logs across the automated test suite and a manual sampling review.
- **SC-004**: 100% of login attempts against DISABLED accounts fail, including attempts using fully correct credentials.
- **SC-005**: 100% of attempts by one user to read or modify another user's protected account information are denied in testing.
- **SC-006**: Automated brute-force simulation (repeated incorrect login attempts) results in zero successful unauthorized logins, with lockout triggered no later than the 5th consecutive failed attempt and cleared automatically after the 15-minute cool-down.
- **SC-007**: 100% of the defined security-sensitive actions (registration, login success/failure, logout, password reset, enable/disable, role change) produce a retrievable audit record during testing.
- **SC-008**: A new user can complete registration and reach their first successful authenticated action in under 2 minutes under normal conditions.
- **SC-009**: The full automated test suite for authentication, authorization, role protection, account status, and the specified security rules passes before the feature is considered complete.
- **SC-010**: 100% of attempts by a user to disable their own account, including Admin users, are denied in testing.
- **SC-011**: 100% of attempts that would reduce the number of ACTIVE Admin accounts to zero (via role change or account disable) are denied in testing; the system never reaches a state with zero ACTIVE Admins.
- **SC-012**: 100% of account status (ACTIVE/DISABLED) change attempts by non-Admin users are denied in testing.
- **SC-013**: 100% of registration and password-reset-confirm attempts with a password shorter than 8 or longer than 128 characters are rejected in testing; passwords within that range are accepted regardless of character composition.
- **SC-014**: 100% of the 6th-and-beyond request within any 15-minute window from one source IP to `/auth/register` or `/auth/password-reset/request` are rejected (HTTP 429) in testing.
- **SC-015**: 100% of registration attempts using an email that differs only by letter case from an already-registered email are rejected as duplicates in testing; login succeeds regardless of case used at registration vs. login time.
- **SC-016**: Automated testing demonstrates that the response time for a login attempt against a nonexistent email is not distinguishable from a login attempt with an incorrect password against an existing email (both exercise the same password-verification code path).

## Assumptions

- "View their own profile" in scope for this feature means read access to the user's own profile data; profile editing beyond password reset is not required by this feature unless specified elsewhere.
- Account identifier for registration/login is assumed to be an email address, consistent with the password-reset flow needing a delivery channel; this can be revisited if LocalFix uses a different identifier.
- "Important authentication and account-security actions" for auditability (FR-024) is interpreted as: registration, login success, login failure, logout, password reset, account enable/disable, and role change. This list can be expanded later without contradicting this spec.
- Multiple concurrent sessions per user (e.g., logged in on two devices) are assumed to be allowed; logout and expiration apply per-session, not account-wide, unless clarified otherwise.
- Session expiration duration and password-reset link lifetime are left as policy values to be defined during planning (e.g., standard web-session and reset-link durations), since no specific values were provided and none affect scope or security posture at the specification level.
- "At least one active Admin must remain" is enforced at the point of the role-change or disable action (reject the action if it would drop the count to zero); it does not require seeding more than one Admin initially, only that the last remaining one cannot be demoted or disabled.
- API documentation exposure (whether `/docs`/`/redoc`/`/openapi.json` are served) is treated as a deployment/environment configuration concern rather than feature behavior, and is tracked in plan.md's Security Hardening Addendum rather than as a functional requirement here.
- CORS policy (F9 from the 2026-10-06 security review), Argon2 cost-parameter tuning (F12), and structured application logging/health-check endpoints (F13) are explicitly deferred: CORS has no frontend consumer yet to design against, Argon2 tuning needs real deployment capacity data, and logging/health-endpoints are cross-cutting observability concerns better scoped as a separate future feature than retrofitted into this one.

## Clarifications

### Session 2026-10-06

- Q: How are the Officer and Admin roles ever assigned, given that users cannot self-assign them? → A: An Admin can promote/assign roles to existing user accounts (User Story 2a, FR-004a–FR-004c); this is in scope for this feature.
- Q: What verification step proves account ownership during password reset? → A: A single-use, time-limited link sent to the account's registered email (User Story 5, FR-010–FR-010b).
- Q: What are the specific brute-force protection parameters? → A: Per-account lockout after 5 consecutive failed attempts, with a 15-minute cool-down (User Story 7, FR-022–FR-022a).
- Q: Who can enable or disable a user account, and can a user disable their own account? → A: Only an Admin may change account status; a user (including an Admin) must not be able to disable their own account (User Story 2b, FR-019a–FR-019c).
- Q: Can an Admin remove their own Admin role, and what happens if that would leave zero Admins? → A: An Admin must not be able to remove their own Admin role, and the system must always keep at least one ACTIVE Admin account, whether the action is a role change or an account disable (FR-004d, FR-004e, FR-019d).
- Q: Is the session expiration duration decided now or deferred? → A: Sessions must expire after a defined period; the exact duration is deferred to the planning phase (confirms existing Assumption, no spec change needed).

### Session 2026-10-07 (post-implementation security review F1–F13)

- Q: What are the password length bounds, and are complexity rules required? → A: 8–128 characters, no forced complexity rules beyond length (FR-028, SC-013).
- Q: What are the rate-limiting thresholds for registration and password-reset-request, and what backs them? → A: 5 requests per 15 minutes per source IP, enforced via the existing PostgreSQL-backed pattern — no new infrastructure (FR-030, SC-014).
- Q: Must email matching be case-insensitive? → A: Yes, for both uniqueness and login lookup (FR-029, SC-015).
- Q: Must authentication-failure timing, not just response body, avoid revealing account existence? → A: Yes — this strengthens FR-020 (FR-031, SC-016).
- Q: Are F9 (CORS), F12 (Argon2 cost tuning), and F13 (structured logging/health endpoint) in scope for this feature? → A: No — explicitly deferred (see Assumptions).
