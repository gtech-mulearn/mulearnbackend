# Add the record_submission and peer_approve commands

| | |
|---|---|
| ID | 0084 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | M |
| Labels | arch, phase:4, module:contributions, type:feature, size:M, core-review |
| Depends on | 0027, 0059, 0082 |
| Blocks | 0085 |
| Repos | mulearnbackend |

## Why

Every channel (dashboard, app, Discord, partners) records submissions the same way, and the first approval by a peer goes through one command ([ADR-018](../adr/ADR-018-channel-agnostic-contributions.md)).

## Before you start

- Issues 0027 (authorization), 0059 (outbox) and 0082 must be merged.

## What to do

1. Add these commands in `modules/contributions/services/commands.py`, each `@command(owner="contributions")`:
   - `record_submission(*, principal, task_id, source, source_ref, proof) -> SubmissionResult`. It requires `contributions.record_submission`. It is idempotent on `(source, source_ref)`: a replay returns the existing submission with `created=False`. It publishes `SubmissionRecorded` (v1).
   - `peer_approve(*, principal, submission_id) -> SubmissionResult`. It requires `contributions.peer_approve`, refuses self-approval, and locks the submission row.
2. Register the policies in `modules/contributions/policies.py`. Any verified learner may record their own submission; peer approval is any verified learner other than the owner.
3. Export both from `public.py`, with their DTOs and events in `contracts.py`.
4. Add service tests (SQLite) and MySQL-tier tests for the replay behaviour.

## Acceptance criteria

- [ ] Recording the same `source_ref` twice creates one submission.
- [ ] Self peer-approval is refused.
- [ ] Each successful command publishes exactly one event.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Appraisal and awards (issue 0085).

## Notes for reviewers

Check the lock order is documented and followed: submission first.
