# Treat Django deprecation warnings as errors in new code

| | |
|---|---|
| ID | 0041 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | S |
| Labels | arch, phase:2, module:platform, type:chore, size:S |
| Depends on | 0014 |
| Blocks | 0042 |
| Repos | mulearnbackend |

## Why

Django announces removals with deprecation warnings, and today they are invisible. Turning them into errors for new code keeps new code upgrade-ready, without blocking on legacy code ([ADR-051](../adr/ADR-051-toolchain.md)).

## Before you start

- Issue 0014 must be merged.

## What to do

1. In the pytest configuration, add `filterwarnings` entries that turn `RemovedInDjango50Warning`, `RemovedInDjango51Warning` and `RemovedInDjango60Warning` into errors when raised from `building_blocks`, `modules` or `tests`.
2. Make the `legacy` CI job print the count of deprecation warnings from legacy code.
3. Add a test that raises a Django removal warning from a module under `building_blocks/tests/` and checks pytest treats it as an error.

## Acceptance criteria

- [ ] A deprecation warning raised in new code fails the run.
- [ ] Legacy warnings don't fail the run, but they are counted in CI output.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Fixing legacy deprecations (as part of 0042).

## Notes for reviewers

Check the filter is scoped by module, so legacy code isn't affected.
