# Create the contributions module and its models

| | |
|---|---|
| ID | 0081 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M, core-review, needs-db-change |
| Depends on | 0012, 0023, 0080 |
| Blocks | 0082, 0087, 0093 |
| Repos | mulearnbackend |

## Why

`contributions` is the first business module. It owns submissions, the ledger and the karma column of the wallet ([modules/contributions.md](../modules/contributions.md)).

## Before you start

- Issues 0023 (the generator) and 0080 (applied) must be merged.
- Issue 0012 must also be merged.

## What to do

1. Run `python manage.py new_module contributions`.
2. Create `modules/contributions/data/models.py` with these `managed = False` models:
   - `KarmaActivityLogRow` (table `karma_activity_log`: the fields the module needs, plus the four new columns);
   - `WalletRow` (table `wallet`: `id`, `user_id`, `karma`, `karma_last_updated_at`, `updated_at`; **not** `coin`, which is frozen);
   - `LedgerEntryRow` (table `karma_ledger_entry`).

   Reference other modules' rows as id columns, never as `ForeignKey`s.
3. Create `modules/contributions/data/task_snapshot.py`: a read-only `TaskRow` mapping of `task_list` (`id`, `hashtag`, `karma`, `ig_id`, `active`). Make it read-only: its `save` and `delete` raise. It is a transitional read until `learning` exists.
4. Create `tests/architecture/allowlists/legacy_writers.toml` with a `[reads]` section listing that mapping (`modules/contributions/data/task_snapshot.py::TaskRow`). Issue 0095 adds the writers to the same file. Add `tests/architecture/test_legacy_reads.py`: every `[reads]` entry exists and refuses `save` and `delete`.
5. Add `contributions` to `tests/architecture/module_graph.toml`, allowed to depend on nothing yet, and regenerate `.importlinter`.
6. Update `docs/architecture/modules/contributions.md` with the models, and note the transitional read.

## Acceptance criteria

- [ ] The parity test passes for the new models.
- [ ] `lint-imports` and the fitness functions pass.
- [ ] No legacy code changes.

## How to test

```sh
scripts/test.sh --mysql tests/schema/ modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Commands (issues 0084–0086).

## Notes for reviewers

Check that `WalletRow` doesn't map the frozen `coin` column.
