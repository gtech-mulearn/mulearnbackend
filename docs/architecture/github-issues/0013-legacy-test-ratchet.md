# Record the legacy test baseline and fail only on new failures

| | |
|---|---|
| ID | 0013 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | M |
| Labels | arch, phase:1, module:platform, type:chore, size:M |
| Depends on | 0011 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

The legacy test suite already has failures. A rule that demands zero failures can't be switched on, and no rule at all lets new failures slip in. A ratchet records today's failures and fails CI only on new ones ([ADR-016](../adr/ADR-016-architecture-enforced-by-automation.md)).

## Before you start

- Issue 0011 must be merged.

## What to do

1. Run the whole suite with `scripts/test.sh --junitxml=legacy.xml` (the SQLite tier).
2. Create `tests/legacy_baseline.txt`, listing the node ids that fail or error today, one per line and sorted.
3. Create `scripts/legacy_ratchet.py`. It reads the JUnit XML and the baseline, then:
   - exits 1 if any test **not** in the baseline fails or errors;
   - prints, without failing, baseline tests that now pass, so they can be removed.
4. Add a `legacy` job to `ci.yml` that runs the suite and then the ratchet script.
5. Add `tests/test_legacy_ratchet.py` for the script, using small XML fixtures.

## Acceptance criteria

- [ ] The `legacy` job passes on `dev` as it is.
- [ ] A new failing legacy test fails the job; a baseline test that starts passing doesn't.
- [ ] The baseline contains test ids only, no output.

## How to test

```sh
scripts/test.sh tests/test_legacy_ratchet.py
```

## Out of scope

- Fixing the legacy failures.

## Notes for reviewers

The baseline should only ever shrink. Point that out in the file's header comment.
