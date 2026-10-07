# LocalFix Constitution

## Core Principles

### I. Security First

The system MUST follow secure development practices.

Authentication, authorization, input validation, secure data handling,
and protection against common web vulnerabilities are mandatory.

### II. Role-Based Authorization

The system MUST enforce role-based access control.

Citizens, officers, and administrators MUST only access functionality
and data permitted by their roles.

### III. Human Accountability for AI

AI MAY provide classifications, priorities, recommendations, and
decision support.

AI MUST NOT have final authority over important civic decisions.

Authorized human users MUST be able to review and override AI decisions.

### IV. Testable Business Rules

All critical business rules and state transitions MUST be covered
by automated tests.

Requirements MUST be written so that their behavior can be verified.

### V. Auditability

Important administrative and security-sensitive actions MUST be
auditable.

Audit records SHOULD identify the actor, action, affected resource,
and timestamp.

## Architecture Principles

The initial system MUST use a modular monolithic architecture.

The system SHOULD maintain clear separation between:

- Presentation
- Application and business logic
- Data access
- Infrastructure

Microservices MUST NOT be introduced unless a specific requirement
justifies their complexity.

## Development Principles

Code MUST prioritize:

- Readability
- Maintainability
- Modularity
- Testability
- Meaningful naming
- Appropriate documentation

Unnecessary complexity MUST be avoided.

## AI Development Principles

AI coding agents MAY assist with:

- Specification analysis
- Architecture proposals
- Code generation
- Test generation
- Documentation
- Refactoring

Human developers MUST review AI-generated code before it is considered
complete.

AI agents MUST NOT independently perform irreversible production changes.

## Security and Privacy

Secrets MUST NOT be committed to source control.

Passwords, API keys, tokens, and credentials MUST be stored using
appropriate environment or secret-management mechanisms.

The system SHOULD collect only information necessary for its operation.

## Testing

Business-critical functionality MUST have automated tests.

API behavior, authorization rules, important state transitions,
and security-sensitive functionality MUST be tested.

## Governance

This Constitution is the highest-level engineering authority for
the LocalFix project.

If a specification, implementation plan, or generated code conflicts
with a MUST-level principle in this Constitution, the conflict MUST
be resolved before implementation is considered complete.

Changes to this Constitution MUST be intentional and documented.

Version: 1.0.0
Ratified: 2026-10-06
Last Amended: 2026-10-06