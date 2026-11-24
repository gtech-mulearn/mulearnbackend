# Add the penalize and adjust commands

| | |
|---|---|
| ID | 0086 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M, core-review |
| Depends on | 0085 |
| Blocks | 0091 |
| Repos | mulearnbackend |

## Why

Moderators need to penalise misconduct, and admins need audited corrections. Both go through the ledger with clear rules: only penalties may take karma below zero ([ADR-004](../adr/ADR-004-karma-ledger.md)).

## Before you start

- Issue 0085 must be merged.

## What to do

1. Add these commands:
   - `penalize(*, principal, user_id, amount, reason, source_ref) -> EntryResult`. It requires `contributions.penalize`, held by Discord Moderators and admins. It appends a negative `penalty` entry, which may take the balance below zero, and publishes `KarmaPenalized`.
   - `adjust(*, principal, user_id, delta, reason) -> EntryResult`. It requires `contributions.adjust`, held by admins and never for one's own account. A negative adjustment that would go below zero is refused. It publishes `KarmaAdjusted`.
2. Store the reason and the actor in the entry's `reason` and `created_by`.
3. Add tests for both rules and the self-adjustment refusal.

## Acceptance criteria

- [ ] A penalty can take a balance negative; an adjustment can't.
- [ ] Self-adjustment is refused.
- [ ] Every entry records its actor and reason.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- A user interface for moderators.

## Notes for reviewers

Check the role names used by the policies exist in `role`.
