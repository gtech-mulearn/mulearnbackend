# Add safe_enqueue for legacy .delay() calls

| | |
|---|---|
| ID | 0069 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M |
| Depends on | 0059, 0062, 0065 |
| Blocks | 0070 |
| Repos | mulearnbackend |

## Why

Legacy code calls `.delay()` inside request transactions. A task can then run before the data it needs commits, or a broker outage turns a committed request into an error. `safe_enqueue` sends after commit, and falls back to the outbox ([ADR-041](../adr/ADR-041-transactions-and-consistency.md)).

## Before you start

- Issues 0059 (outbox) and 0065 (task base) must be merged.
- Issue 0062 must also be merged.

## What to do

1. Add `safe_enqueue(task, *args, **kwargs) -> None` to `building_blocks/tasks.py`:
   - inside a transaction, it registers `transaction.on_commit` to send;
   - outside one, it sends now;
   - if the broker raises during the send, it writes an outbox row of type `internal.task_enqueue` with the task name and arguments instead. The relay dispatches it later.
2. Teach `dispatch` (from issue 0062) to run `internal.task_enqueue` rows by calling the named task.
3. Add tests:
   - a rollback sends nothing;
   - a commit sends once;
   - a broker failure writes an outbox row, which the relay then dispatches.

## Acceptance criteria

- [ ] All tests pass.
- [ ] Arguments must be JSON-serialisable; a non-serialisable argument raises at the call site.

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Replacing call sites (issue 0070).

## Notes for reviewers

Check the fallback can't lose the task when both the broker and the database fail. It should raise then.
