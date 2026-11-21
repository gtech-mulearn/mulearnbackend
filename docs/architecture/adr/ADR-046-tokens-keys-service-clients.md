# ADR-046: Tokens, keys and service clients

Status: Accepted (new on 2026-11-21; amends ADR-008)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started.

## Context

Several services and clients exchange tokens: the backend, the authserver, the media worker, the
Discord bot, the scheduler, and later partners and AI agents. Each signing purpose needs its own
key, keys must rotate without logging anyone out, and services must authenticate as themselves.
The authserver already offers OIDC with asymmetric keys.

## Options considered

- **Jump straight to RS256 everywhere.**
- **Two phases: key separation first, then RS256 with JWKS.**
- **Keep symmetric tokens with one shared key.**

## Decision

**Phase 1 (no client change):**
- **One key per signing purpose:** access and refresh tokens (with a `kid`), the partner-token
  key, and the learning-circle HMAC. No key serves two purposes.
- **Rotation without logouts.** During a rotation, tokens signed with the previous key are accepted
  for the refresh-token lifetime (7 days). The previous key is then dropped.
- **`SECRET_KEY` rotates through `SECRET_KEY_FALLBACKS`.**
- **Upload tickets.** A service that only needs to check an upload holds a ticket key, never a
  token signing key.
  - The backend mints short-lived upload tickets: an HMAC over the user id, purpose, maximum
    size and a 5-minute expiry, with a key held only by the backend and the media worker.
  - The media worker verifies only those tickets.
- **Service credentials authenticate a service.** They never mint user tokens. Acting on behalf
  of a member is an explicit, scoped and audited `act_as` capability.
- There is a rotation runbook.

**Phase 2 (deferred, or earlier if a partner needs it):**
- RS256 access tokens from the authserver's JWKS, with `iss`, `aud` and `token_use=access`, and a
  15-minute lifetime.
- Rotating refresh tokens with reuse detection.
- Revocation by a per-user `auth_epoch`, bumped on logout-all, credential reset, suspension or grant
  revocation.
- Authorization never reads roles from tokens ([ADR-007](ADR-007-scoped-grants-and-policies.md)). Claims that clients read stay
  ([ADR-044](ADR-044-api-standards-v1-2.md)).

**Service-to-service:**
- A `service_client` table (hashed secret, scopes, rate quota and capabilities) replaces
  environment lists.
- **Partners and AI agents** use OIDC client credentials with scopes `mulearn.<module>.read|write`.
  This is built when the first partner signs. Every call is audited, and writes require
  `Idempotency-Key`.

**Webhooks:** provider signature verification, plus idempotency on the provider's event id.

### Refinements (2026-11-21)

- `mucoin-service` follows the same rule as the media worker: it holds a ticket key and a webhook secret, never a token signing key. Until phase 2 gives it JWKS, it accepts short-lived tickets minted by the backend ([ADR-054](ADR-054-mucoin-external-consumer.md)).
- An upload ticket carries a `jti` for best-effort single use. The worker returns an upload receipt, an HMAC over key, user and purpose, which the backend verifies when the key is attached to a record.

## Consequences

- A compromised or misused key has a small blast radius.
- Rotations become routine.

## Revisit when

- There are more than 10 partners. Then consider an API gateway.

## Related ADRs

[ADR-007](ADR-007-scoped-grants-and-policies.md), [ADR-008](ADR-008-authserver-separate-idp.md), [ADR-011](ADR-011-object-storage-stateless-nodes.md), [ADR-021](ADR-021-separate-identity-schema.md), [ADR-044](ADR-044-api-standards-v1-2.md)
