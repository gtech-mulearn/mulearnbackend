# Add MySQL concurrency tests for awards

| | |
|---|---|
| ID | 0088 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:chore, size:M |
| Depends on | 0012, 0085 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Correctness under concurrency is the reason the ledger exists. It must be proven on real MySQL, with real locks.

## Before you start

- Issues 0012 and 0085 must be merged.

## What to do

1. Create `modules/contributions/tests/mysql/test_concurrency.py` with these tests, using threads and a barrier:
   - two appraisers approving the same submission at once produce one award;
   - the same Discord message recorded twice at once produces one submission;
   - an approval and a reversal racing end in a consistent state (balance equals ledger sum);
   - a reversal before its award is refused.
2. Run each test 20 times in CI to catch flakiness.

## Acceptance criteria

- [ ] All tests pass 20 times in a row on the MySQL tier.
- [ ] `wallet.karma` equals the ledger sum after every test.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/mysql/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Load testing (the Discord storm scenario is run on staging).

## Notes for reviewers

Check the tests really overlap: assert that both threads were inside the command at once.
