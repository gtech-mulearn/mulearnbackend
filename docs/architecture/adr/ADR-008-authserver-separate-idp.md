# ADR-008: The authserver remains a separate identity provider

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: partly in place. The authserver is already a separate service; resolving grants in the backend ([ADR-007](ADR-007-scoped-grants-and-policies.md)) is not started.

## Context

The authserver hosts login, OTP, social sign-in and an OIDC provider for partners and
first-party clients. The maintainers require identity to be a separate system: a separate
process, data, keys and scaling.

## Options considered

- **Keep the authserver as a separate IdP;** the backend is a resource server.
- **Fold identity back into the backend:** login storms and API load would share one failure
  domain.
- **A hosted IdP:** a new processor and residency question, and the existing OIDC investment is
  lost.

## Decision

- The authserver is the identity provider:
  - its own deployable;
  - its own schema ([ADR-021](ADR-021-separate-identity-schema.md));
  - its own database user, keys and secrets.
- It owns identity, credentials, federation and sessions.
- The backend is a resource server that resolves grants itself and never authorizes from token
  role claims ([ADR-007](ADR-007-scoped-grants-and-policies.md)).
- **Changes (2026-11-21):**
  - the token, key and service-client strategy moves to [ADR-046](ADR-046-tokens-keys-service-clients.md);
  - the provisioning contract between the authserver and the backend is defined there;
  - the authserver follows its own upgrade track onto the same base image and Django LTS as the
    backend ([ADR-050](ADR-050-platform-versions.md)).

## Consequences

- A clear security and scaling boundary: login storms scale the IdP, not the API.
- Releases that change tokens or provisioning are coordinated between the two repositories.

## Revisit when

- The number of partner integrations makes an API gateway worthwhile.

## Related ADRs

[ADR-007](ADR-007-scoped-grants-and-policies.md), [ADR-021](ADR-021-separate-identity-schema.md), [ADR-046](ADR-046-tokens-keys-service-clients.md), [ADR-050](ADR-050-platform-versions.md)
