# Route utils/karma.py through contributions behind a flag

| | |
|---|---|
| ID | 0095 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | L |
| Labels | arch, phase:4, module:contributions, type:feature, size:L, core-review |
| Depends on | 0025, 0074, 0085 |
| Blocks | 0096, 0097, 0098, 0099 |
| Repos | mulearnbackend |

## Why

`utils/karma.py` `add_karma` and `remove_karma` are the shared helpers most karma writes go through. Routing them through `contributions` behind a flag moves the largest share of writers in one step. An allowlist then makes sure no new direct writer appears ([ADR-038](../adr/ADR-038-modules-own-their-tables.md)).

## Before you start

- Issues 0025, 0074 (flags) and 0085 must be merged.
- Read `utils/karma.py`: `add_karma(user_id, hashtag, approved_by, karma=None)` and `remove_karma(user_id, hashtag, karma=None, removed_by=None)`, and the `contributions` page in [modules/](../modules/contributions.md).

## What to do

1. Declare the flag `contributions.ledger_writes` (kind `release`, owner `contributions`, default off, expiring 2027-06-30) in `modules/contributions/flags.py`.
2. Write characterization tests for `add_karma` and `remove_karma`: rows written, wallet change, notifications sent.
3. When the flag is on:
   - `add_karma` calls `contributions.public.award_direct` once per user, with `source="legacy"` and `source_ref="kal:<new karma_activity_log id>"`, keeping the karma-log row it creates today;
   - `remove_karma` reverses the matching award entry through `reverse_award`.

   When it is off, nothing changes. Notifications stay as they are.

   With the flag on or off, set the new `karma_activity_log.source` column to `legacy` on the rows `add_karma` creates, so reconciliation (issue 0100) can tell backend rows from rows written outside the backend.
4. Add a writers section to `tests/architecture/allowlists/legacy_writers.toml` (issue 0081 created the file) listing today's direct writers of `karma_activity_log` and `wallet` (`file::function`, from the scan in the `contributions` module page). Mark `api/dashboard/referral/referral_view.py::post` as the frozen coin writer: it writes only `wallet.coin` ([ADR-054](../adr/ADR-054-mucoin-external-consumer.md)), and it stays listed after the cut-over.
5. Add `tests/architecture/test_legacy_writers.py`, an AST scan that fails if a new function outside `modules/contributions` writes those models. A stale entry fails too.

## Acceptance criteria

- [ ] The characterization tests pass with the flag off and on.
- [ ] With the flag on, every `add_karma` call produces one ledger entry, and the wallet stays equal to the ledger sum.
- [ ] The writers test fails on a new direct writer.

## How to test

```sh
scripts/test.sh --mysql tests/characterization/ modules/contributions/tests/ tests/architecture/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Other writers (issues 0096–0099).

## Notes for reviewers

The flag-off path must be exactly today's behaviour. Two reviewers.
