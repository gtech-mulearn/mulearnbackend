# Add balance, entry and appraisal-queue selectors

| | |
|---|---|
| ID | 0087 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M |
| Depends on | 0027, 0081 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Screens and other modules read balances, entries and the appraisal queue through selectors that return DTOs, with bounded query counts.

## Before you start

- Issue 0081 must be merged.
- Issue 0027 must also be merged.

## What to do

1. Create `modules/contributions/selectors/` with:
   - `get_balance(user_id) -> BalanceDTO`, from `wallet.karma`;
   - `ledger_balance(user_id) -> int`;
   - `list_entries(user_id, cursor=None, limit=50) -> EntryPage`, keyset by `id` descending, with `limit` at most 100;
   - `appraisal_queue(principal, cursor=None, limit=50) -> QueuePage`: pending submissions in the principal's appraiser scopes, oldest first;
   - `submission_status(submission_id)`;
   - `task_id_for_hashtag(hashtag)`.
2. Export them from `public.py`.
3. Add query-count tests: each selector runs the same number of queries at limit 1 and limit 100.

## Acceptance criteria

- [ ] All selectors return DTOs, never models or querysets.
- [ ] The query counts are equal at both page sizes.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/selectors/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- HTTP endpoints for these. They come with the screens that need them.

## Notes for reviewers

Check the appraisal-queue query uses an index (run `EXPLAIN` on the MySQL tier).
