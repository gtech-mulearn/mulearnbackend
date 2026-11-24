# Add MuLearnAPIView and PublicAPIView

| | |
|---|---|
| ID | 0026 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M, core-review |
| Depends on | 0019 |
| Blocks | 0027, 0090 |
| Repos | mulearnbackend |

## Why

New endpoints need one base class that applies the API conventions: authentication by default, the envelope, the request id, and explicit public endpoints ([07-api-standards.md](../07-api-standards.md), [04-module-rules.md](../04-module-rules.md#authorization)).

## Before you start

- Issue 0019 must be merged.

## What to do

1. Create `building_blocks/api/views.py`:
   - `MuLearnAPIView(APIView)`: authentication uses the existing token validation (wrap the logic in `utils/permission.py` behind an adapter class, without changing it), `permission_classes` defaults to authenticated, and `self.ok(data, status=200)` returns the envelope;
   - `PublicAPIView(MuLearnAPIView)`: it requires a class attribute `public_reason`, sets permissions to allow-any, and raises at import if `public_reason` is missing.
2. Create `tests/architecture/allowlists/public_views.txt`, listing public module views as `module.ClassName: reason`, with a test that every `PublicAPIView` subclass is listed.
3. Add tests:
   - an anonymous call to a `MuLearnAPIView` gets the legacy token-failure response;
   - an authenticated call gets the envelope;
   - a `PublicAPIView` without a reason fails.

## Acceptance criteria

- [ ] All tests pass.
- [ ] No legacy view changes.

## How to test

```sh
scripts/test.sh building_blocks/tests/ tests/architecture/
```

## Out of scope

- `InternalAPIView` (issue 0090).
- Changing the project-wide DRF defaults (Phase 5).

## Notes for reviewers

Authentication code needs two reviewers. Check the adapter reproduces the legacy token failures exactly.
