# Add property tests for the ledger rules

| | |
|---|---|
| ID | 0083 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:chore, size:M |
| Depends on | 0082 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Ledger rules must hold for every sequence of operations, not only the ones someone thought to test. Hypothesis generates them.

## Before you start

- Issue 0082 must be merged.

## What to do

1. Create `modules/contributions/tests/domain/test_properties.py`, using hypothesis to generate random sequences of `record`, `peer_approve`, `approve`, `reject`, `reverse`, `penalize` and `adjust` against an in-memory model of the domain functions.
2. Check these invariants after every step:
   - the balance equals the sum of entries;
   - no two entries share a key;
   - a reversal applies at most once per entry;
   - only penalty entries take the balance below zero;
   - a negative adjustment never goes below zero;
   - replaying any operation changes nothing.
3. Run at least 2,000 examples in CI.

## Acceptance criteria

- [ ] The property tests pass with 2,000 examples.
- [ ] Breaking any rule in `domain/` (try one) makes them fail with a minimal example.

## How to test

```sh
scripts/test.sh modules/contributions/tests/domain/test_properties.py
```

## Out of scope

- Database behaviour (issue 0088).

## Notes for reviewers

Check the in-memory model uses the real domain functions, not a copy of them.
