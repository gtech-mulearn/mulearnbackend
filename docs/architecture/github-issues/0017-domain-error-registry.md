# Add the DomainError registry with stable codes

| | |
|---|---|
| ID | 0017 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M |
| Depends on | 0014 |
| Blocks | 0019, 0027, 0082 |
| Repos | mulearnbackend |

## Why

Every failure should have a stable, documented `code` that clients can branch on, and a correct HTTP status ([ADR-010](../adr/ADR-010-api-contract-envelope.md), [07-api-standards.md](../07-api-standards.md#the-response-contract)). Today each view builds its own error response.

## Before you start

- Issue 0014 must be merged.

## What to do

1. Create `building_blocks/errors.py`. It is framework-free, so domain code can use it, and imports no Django.
   - `DomainError(Exception)` with class attributes `code`, `http_status`, `title` and `public_message`.
   - Subclasses: `ValidationFailed` (400), `Unauthorized` (401), `Forbidden` (403), `NotFound` (404), `Conflict` (409), `Unprocessable` (422), `RateLimited` (429) and `DependencyUnavailable` (503).
   - `error_code(code: str, title: str)`, a class decorator that registers a subclass under `code`. It rejects a duplicate code and any code not matching `^[a-z_]+\.[a-z_]+$`.
   - `registry() -> dict[str, type[DomainError]]`.
2. Add `building_blocks/tests/test_errors.py`: registration works, duplicates and bad formats raise, and each subclass carries its status.

## Acceptance criteria

- [ ] All tests pass.
- [ ] `building_blocks/errors.py` imports only the standard library.

## How to test

```sh
scripts/test.sh building_blocks/tests/test_errors.py
```

## Out of scope

- Rendering errors as responses (issue 0019).

## Notes for reviewers

The code format is a public contract. Check it is enforced.
