# Add code and requestId to the envelope, with one exception handler

| | |
|---|---|
| ID | 0019 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M |
| Depends on | 0017, 0018 |
| Blocks | 0026 |
| Repos | mulearnbackend |

## Why

Clients need a stable `code` to branch on, and operators need a request id in every response. Both are additive to the existing envelope, so no client breaks ([ADR-010](../adr/ADR-010-api-contract-envelope.md), [07-api-standards.md](../07-api-standards.md#the-response-contract)).

## Before you start

- Issues 0017 (errors) and 0018 (request context) must be merged.
- Read `utils/response.py` (`CustomResponse`) and the compatibility promise in 07-api-standards.md: token failures keep 401/403 with `statusCode 1000`.

## What to do

1. In `utils/response.py` `CustomResponse`, add two keys to every envelope:
   - `code`: `"ok"` on success, or the given code on error;
   - `requestId`: from the request context.

   Existing keys and values stay exactly as they are.
2. Create `building_blocks/api/exceptions.py` with `exception_handler(exc, context)`:
   - a `DomainError` renders the envelope with its `code` and `http_status`;
   - a DRF `ValidationError` renders 400 with `code: validation_error` and the field messages under `message.fields`;
   - an unhandled exception renders a JSON 500 envelope with `code: internal_error`;
   - authentication and permission failures keep the response legacy views produce today.
3. Set `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
4. Add tests on a small test-only view, plus a test on one existing protected route proving that a missing or expired token still returns its current status and `statusCode`.

## Acceptance criteria

- [ ] Every legacy response gains only `code` and `requestId`, with every other key and value unchanged. Prove it with before/after tests on 3 existing routes.
- [ ] Unhandled exceptions return a JSON envelope with status 500.
- [ ] Token failures are unchanged.

## How to test

```sh
scripts/test.sh building_blocks/tests/ utils/tests/
```

## Out of scope

- Changing any legacy status code.
- problem+json.

## Notes for reviewers

This touches every response. Review the before/after tests closely, and check the old-app token behaviour.
