# Add the appraise and reverse_award commands

| | |
|---|---|
| ID | 0085 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | L |
| Labels | arch, phase:4, module:contributions, type:feature, size:L, core-review |
| Depends on | 0016, 0084 |
| Blocks | 0086, 0088, 0091, 0094, 0095 |
| Repos | mulearnbackend |

## Why

Appraisal is the step that awards karma. It must award exactly once per approval, even with two appraisers at once or a replayed reaction, and reversals must be exact ([ADR-004](../adr/ADR-004-karma-ledger.md)).

## Before you start

- Issue 0084 must be merged.
- Issue 0016 must also be merged.

## What to do

1. Add these commands:
   - `appraise(*, principal, submission_id, expected_generation, decision) -> AwardResult`, where `decision` is `approve` or `reject`. It requires `contributions.appraise`. It locks the submission row, then the wallet row. It applies the domain decision, appends an `award` entry keyed with `award_key`, with the amount taken from the task snapshot, the period from `clock.period_key(now)`, and `member_path` and `task_scope_path` set to `"IN"` until chapters exist. It adds the amount to `wallet.karma` with an `F()` expression, and publishes `SubmissionApproved` and `KarmaAwarded`. Rejection publishes `SubmissionRejected`.
   - `reverse_award(*, principal, entry_id, reason) -> ReversalResult`. It requires `contributions.reverse`, appends a `reversal` entry keyed `reversal:<entry_id>` with `reverses_entry_id`, subtracts from `wallet.karma`, and publishes `KarmaReversed`.
   - `award_direct(*, source, source_ref, user_id, amount, reason)`: system awards with no submission. It is idempotent on the key.
2. The policies:
   - `contributions.appraise` is held by verified Appraiser grants, globally or for the task's interest group;
   - `contributions.reverse` is held by admins.
3. Add service and MySQL-tier tests.

## Acceptance criteria

- [ ] An approval produces one ledger entry and one wallet change, and a replay produces none.
- [ ] A stale `expected_generation` changes nothing.
- [ ] A reversal of an already-reversed entry is refused.
- [ ] `wallet.karma` equals the ledger sum after every test.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Publishing `task.verified` to external consumers (on hold with the μCoin integration).

## Notes for reviewers

This is the karma path. Two reviewers; check the lock order and the keys.
