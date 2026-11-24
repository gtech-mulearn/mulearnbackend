# Move the signup wallet write onto contributions

| | |
|---|---|
| ID | 0099 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:chore, size:M, core-review |
| Depends on | 0095, epic:phase-0-security-hardening |
| Blocks | 0104 |
| Repos | mulearnbackend |

## Why

Signup writes karma rows and wallet balances directly. Every karma write must go through `contributions`, so the ledger is the one source of truth ([ADR-004](../adr/ADR-004-karma-ledger.md), [13-migration-strategy.md](../13-migration-strategy.md)).

## Before you start

- Issue 0095 (the ledger-writes flag) must be merged.
- The Phase 0 security epic must be closed.
- Read [Characterization tests before every move](../12-testing-and-quality-gates.md#characterization-tests-before-every-move) and the `contributions` page in [modules/](../modules/contributions.md).
- The write sites, from the AST scan at 7fd66060: `api/register/serializers.py` :: `create` (the wallet row at signup).

## What to do

1. Write characterization tests for every route that reaches these write sites, at the MySQL tier, using the harness from issue 0025. Record the response, the query count and the rows written. Never pin a success that should be a refusal: if a route answers a caller it should refuse, stop and report it privately as `SECURITY.md` describes.
2. Replace each direct write of `KarmaActivityLog` and `Wallet` with a call to `modules.contributions.public`. Use `award_direct` for awards made by the system, and the matching command for approvals and reversals. Do this only when the flag `contributions.ledger_writes` is on, and keep the legacy path when it is off.
3. Use a stable source reference for each award, so a retry can't award twice. Document the format in the `contributions` module page.
4. Remove these write sites from `tests/architecture/allowlists/legacy_writers.toml`.
5. Leave `api/dashboard/referral/referral_view.py` :: `post` on the legacy path, and keep it in the allowlist, marked as the frozen coin writer. Change only its `wallet.save()` to `wallet.save(update_fields=["coin"])`, so a full-row save can no longer overwrite a concurrent `wallet.karma` update. Add a MySQL-tier test for that.

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

Signup must still create the wallet row, through `contributions`. The referral flow is not a karma writer: it only debits `wallet.coin`, which is frozen ([ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).
