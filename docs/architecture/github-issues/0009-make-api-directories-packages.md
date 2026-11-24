# Make every directory under api/ a package

| | |
|---|---|
| ID | 0009 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | S |
| Labels | arch, phase:1, module:platform, type:chore, size:S |
| Depends on | 0002 |
| Blocks | 0014 |
| Repos | mulearnbackend |

## Why

Import tools such as import-linter only see Python packages. At `dev` 7fd66060 only about 30 of the 91 directories under `api/` have an `__init__.py`, so most of the legacy code is invisible to the boundary checks that keep the architecture from eroding ([ADR-016](../adr/ADR-016-architecture-enforced-by-automation.md)).

## Before you start

- Issue 0002 (the safe test runner) must be merged.
- Read [How CI enforces each rule](../04-module-rules.md#how-ci-enforces-each-rule).

## What to do

1. Run a scan for directories under `api/` (excluding `api/launchpad/`, which is deprecated) that contain `.py` files but no `__init__.py`.
2. Add an empty `__init__.py` to each of them.
3. Run the test suite before and after, with `--collect-only -q`, and compare the counts.
4. If two test modules now collide on a package name, fix it by adding the missing `__init__.py` in the `tests` directory as well. Don't rename modules.

## Acceptance criteria

- [ ] No directory under `api/` (except `api/launchpad/`) contains `.py` files without an `__init__.py`.
- [ ] `scripts/test.sh --collect-only -q` collects the same number of tests as before, and every collected test still runs.
- [ ] No other file changes.

## How to test

```sh
scripts/test.sh --collect-only -q
```

## Out of scope

- Fixing any test failures that already exist.
- `api/launchpad/`.

## Notes for reviewers

This pull request should touch only new empty files. Check the collected-test count in the description.
