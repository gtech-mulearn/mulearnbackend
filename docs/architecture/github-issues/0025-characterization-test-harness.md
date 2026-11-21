# Add the characterization-test harness

| | |
|---|---|
| ID | 0025 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | M |
| Labels | arch, phase:1, module:platform, type:chore, size:M |
| Depends on | 0012 |
| Blocks | 0040, 0095 |
| Repos | mulearnbackend |

## Why

Before any legacy route moves into a module, its current behaviour is pinned by tests: the response shape, the status codes and the query count. The harness makes those tests quick to write ([12-testing-and-quality-gates.md](../12-testing-and-quality-gates.md#characterization-tests-before-every-move)).

## Before you start

- Issue 0012 (the MySQL tier) must be merged.
- Read how the backend validates tokens in `utils/permission.py`, so test tokens are minted the same way.

## What to do

1. Create `tests/characterization/conftest.py` with these fixtures:
   - `make_user(roles=())`, a minimal user plus wallet plus role links, built with factory_boy;
   - `api_client(user)`, a DRF `APIClient` with a valid token for that user, minted the way the backend validates it;
   - `assert_envelope(response, *, has_error, status_code)`.
2. Add `golden(response, name)`. It compares a normalised JSON body (ids and timestamps replaced by placeholders) with `tests/characterization/golden/<name>.json`. The pytest option `--update-golden` rewrites the file.
3. Write one example characterization test, for `GET /api/v1/dashboard/profile/user-profile/`, at the MySQL tier.

## Acceptance criteria

- [ ] The example test passes on the MySQL tier.
- [ ] Changing the response shape makes it fail with a readable diff.
- [ ] Fixtures create only what each test needs.

## How to test

```sh
scripts/test.sh --mysql tests/characterization/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Characterization tests for specific routes (each move issue writes its own).

## Notes for reviewers

Check that the normalisation never hides a real field change.
