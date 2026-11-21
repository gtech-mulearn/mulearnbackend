# Add a command that classifies existing karma rows

| | |
|---|---|
| ID | 0093 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M, core-review |
| Depends on | 0081 |
| Blocks | 0094 |
| Repos | mulearnbackend |

## Why

Existing karma rows have no source reference or status, so they can't take part in the ledger's idempotency. Classifying them is the first step of the backfill.

## Before you start

- Issue 0081 must be merged.

## What to do

1. Create `modules/contributions/management/commands/contributions_classify.py`, with `--batch 5000`, `--after-id`, `--max-batches` and `--dry-run` (the default). For each existing `karma_activity_log` row, it sets:
   - `source` and `source_ref`: `discord` / `discord:<task_message_id>` when `task_message_id` is set; otherwise `legacy` / `kal:<id>`;
   - `status`, from `peer_approved` and `appraiser_approved`;
   - `award_generation` = 1 for approved rows.
2. Don't classify rows whose `source_ref` would collide with another row's. Report them instead.
3. Print a report: counts per source and status, and collisions.
4. Process rows in id order. Each batch is its own transaction, and the command resumes with `--after-id`.

## Acceptance criteria

- [ ] The dry run writes nothing and prints the report.
- [ ] A real run is resumable and idempotent: running it twice changes nothing the second time.
- [ ] Collisions are reported, never overwritten.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Running it on production (issue 0104).

## Notes for reviewers

Check the batch size and that each batch commits separately, so locks stay short.
