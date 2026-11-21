# Add the persisted feature flag store

| | |
|---|---|
| ID | 0074 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M, needs-db-change |
| Depends on | 0012, 0021, 0071, 0073 |
| Blocks | 0095 |
| Repos | mulearnbackend |

## Why

Behaviour changes in the migration ship behind flags, each with an owner and an expiry, and every change to a flag is audited ([ADR-031](../adr/ADR-031-feature-flags.md)).

## Before you start

- Issues 0021 and 0073 (applied) must be merged.
- Issues 0012 and 0071 must also be merged.

## What to do

1. Add `managed = False` models for `feature_flag` and `feature_flag_change`.
2. Create `building_blocks/flags.py`:
   - `declare(key, *, kind, owner, expires, default, flip_by=None)`, called from each module's `flags.py`;
   - `is_on(key, *, user_id=None) -> bool`. Percent rollouts bucket by a stable hash of `key:user_id`. It reads a snapshot cached on the `state` alias for 30 s. If the store is unavailable, it returns the declared default; a flag guarding a write must declare a fail-closed default.
3. Create `building_blocks/management/commands/flag.py` (`manage.py flag set <key> on|off|<percent> --reason "..."`). It writes the change row in the same transaction.
4. Create `tests/architecture/test_flags.py`. It fails when a release flag has expired, or a shadow flag's `flip_by` date has passed.
5. Add tests: bucketing stability and defaults when the store is down on the SQLite tier, with the store faked; audit rows in `building_blocks/tests/mysql/test_flags_store.py`, on the MySQL tier.

## Acceptance criteria

- [ ] All tests pass.
- [ ] Every change made through the command leaves an audit row.
- [ ] An expired flag fails CI.

## How to test

```sh
scripts/test.sh building_blocks/tests/ tests/architecture/
scripts/test.sh --mysql building_blocks/tests/mysql/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Migrating existing toggles. Each moves with its module.

## Notes for reviewers

Check the fail-closed rule for write-guarding flags.
