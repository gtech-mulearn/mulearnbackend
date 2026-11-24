# Add nightly karma reconciliation in ticket mode

| | |
|---|---|
| ID | 0100 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M |
| Depends on | 0067, 0094 |
| Blocks | 0104 |
| Repos | mulearnbackend |

## Why

While writers are being moved, a nightly job compares every wallet with its ledger sum. Drift opens a ticket during the migration, and pages after the cut-over ([ADR-004](../adr/ADR-004-karma-ledger.md), [11-reliability-and-observability.md](../11-reliability-and-observability.md#slos-and-alerts)).

## Before you start

- Issues 0067 (schedule claims) and 0094 must be merged.

## What to do

1. Add `run_reconciliation()` in `modules/contributions/services/reconciliation.py`. In user-id batches, it compares `wallet.karma` with the ledger sum, and records drifting users and amounts in the structured log, plus a metric `karma_drift_users`. For each drifting user it also reports the drift **per source**: the karma of `karma_activity_log` rows that have no matching ledger entry, grouped by the row's `source`. `legacy` rows without an entry are expected while the user's flag is off. Rows with no `source` are reported as `unattributed`: until the cut-over these are the Discord bot's direct writes. Any remainder is reported as `unexplained`.
2. Add a scheduled task `contributions.reconcile_nightly` on the `bulk` queue at 03:15 IST, wrapped with `@scheduled`.
3. Add `manage.py contributions_reconcile --user <id>`, for one-off checks.
4. Configure the alert as a ticket (not a page) while the flag is below 100%.
5. Add tests on the MySQL tier with a seeded drift.

## Acceptance criteria

- [ ] Seeded drift is reported with the right users, amounts and sources.
- [ ] No drift reports nothing.
- [ ] The job runs once per night even with two beats.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Paging, which comes after the cut-over epic.
- Discord reconciliation (the cut-over epic).

## Notes for reviewers

Check that the batch queries are indexed and cheap.
