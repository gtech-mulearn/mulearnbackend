# Add the submission state machine and ledger key rules

| | |
|---|---|
| ID | 0082 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M |
| Depends on | 0017, 0081 |
| Blocks | 0083, 0084 |
| Repos | mulearnbackend |

## Why

The rules of a submission's life (who may approve it, what a replay does, how re-awards are keyed) must live in one pure module that the commands call. Then they can be tested without a database ([ADR-004](../adr/ADR-004-karma-ledger.md)).

## Before you start

- Issue 0081 must be merged.
- Issue 0017 must also be merged.

## What to do

1. Create `modules/contributions/domain/submission.py`, framework-free:
   - the states `submitted`, `peer_approved`, `approved`, `rejected`, `reversed`, and the transitions allowed between them;
   - `approve(state, generation, expected_generation, appraiser_id, owner_id) -> Decision`. Approving at the current generation is a no-op that returns the existing result. A stale `expected_generation` raises `StaleGeneration`. Self-approval raises `SelfApprovalNotAllowed`. Approving from `reversed` is a re-award at the next generation;
   - the same pattern for `reject`, `reverse` and `peer_approve`.
2. Create `modules/contributions/domain/keys.py`:
   - `award_key(source_ref, generation)`: `source_ref` for generation 1, `f"{source_ref}#{generation}"` after;
   - `reversal_key(entry_id)`: `reversal:<id>`;
   - `direct_key(kind, ref)`: for system awards, for example `kal:<id>` or `lc:<kind>:<id>`.
3. Create `modules/contributions/domain/errors.py` with registered `DomainError`s.
4. Add unit tests for every transition and key.

## Acceptance criteria

- [ ] All tests pass with no database.
- [ ] `domain/` imports nothing from Django (the import contract checks this).

## How to test

```sh
scripts/test.sh modules/contributions/tests/domain/
```

## Out of scope

- Persistence (issue 0084 onwards).

## Notes for reviewers

Check the re-award and replay rules against ADR-004.
