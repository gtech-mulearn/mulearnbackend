# Move learning-circle karma writes onto contributions

| | |
|---|---|
| ID | 0096 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:chore, size:M, core-review |
| Depends on | 0095, epic:phase-0-security-hardening |
| Blocks | 0104 |
| Repos | mulearnbackend |

## Why

The learning-circle code writes karma rows and wallet balances directly. Every karma write must go through `contributions`, so the ledger is the one source of truth ([ADR-004](../adr/ADR-004-karma-ledger.md), [13-migration-strategy.md](../13-migration-strategy.md)).

## Before you start

- Issue 0095 (the ledger-writes flag) must be merged.
- The Phase 0 security epic must be closed.
- Read [Characterization tests before every move](../12-testing-and-quality-gates.md#characterization-tests-before-every-move) and the `contributions` page in [modules/](../modules/contributions.md).
- The write sites, from the AST scan at 7fd66060: `api/dashboard/lc/dash_lc_serializer.py` :: `create` and `api/dashboard/lc/dash_lc_view.py` :: `post`.

## What to do

1. Write characterization tests for every route that reaches these write sites, at the MySQL tier, using the harness from issue 0025. Record the response, the query count and the rows written. Never pin a success that should be a refusal: if a route answers a caller it should refuse, stop and report it privately as `SECURITY.md` describes.
2. Replace each direct write of `KarmaActivityLog` and `Wallet` with a call to `modules.contributions.public`. Use `award_direct` for awards made by the system, and the matching command for approvals and reversals. Do this only when the flag `contributions.ledger_writes` is on, and keep the legacy path when it is off.
3. Use a stable source reference for each award, so a retry can't award twice. Document the format in the `contributions` module page.
4. Remove these write sites from `tests/architecture/allowlists/legacy_writers.toml`.

## Acceptance criteria

- [ ] The characterization tests pass unchanged with the flag off and with the flag on.
- [ ] With the flag on, each award produces exactly one ledger entry, and `wallet.karma` equals the ledger sum for the affected users.
- [ ] The allowlist entries are removed, and the allowlist test passes.

## How to test

```sh
scripts/test.sh --mysql tests/characterization/ modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Changing what the routes return.
- Notifications, which keep working through the existing `notify_karma_change` call.

## Notes for reviewers

Check each source-reference format is stable across retries, and that the flag-off path is byte-for-byte the old behaviour.
