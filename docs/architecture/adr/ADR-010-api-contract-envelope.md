# ADR-010: API contract 1.1 (additive) on `/api/v1`

Status: Accepted (the standards continue in ADR-044)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: partly in place. The envelope `{hasError, statusCode, message, response}` exists (`utils/response.py` `CustomResponse`); `code`, `requestId` and the single exception handler do not.

## Context

First-party clients depend on the current response envelope, and old mobile builds stay installed
for months. HTTP statuses are inconsistent across endpoints. Clients need a stable code to branch
on, and operators need a request id to correlate with logs.

## Options considered

- **Keep the envelope and add fields** (`code`, `requestId`).
- **Introduce `/api/v2` with a new format:** a big-bang migration for every client.

## Decision

- Keep the envelope `{hasError, statusCode, code, message{general, fields}, response, requestId}`
  on `/api/v1`.
- **Errors** are `DomainError` subclasses with a registered, stable `code`. One exception handler
  turns every error into the envelope.
- Legacy responses only gain the two additive keys.
- Correct HTTP statuses are adopted per module, after client checks.
- `/api/v2` is used only for non-additive redesigns.
- The rest of the API standards are in [ADR-044](ADR-044-api-standards-v1-2.md).

## Consequences

- No client migration.
- Some legacy inconsistency remains until each module migrates.
- Removing or renaming an error code is a breaking change.

## Revisit when

- A redesign is needed that can't be expressed additively.

## Related ADRs

[ADR-044](ADR-044-api-standards-v1-2.md)
