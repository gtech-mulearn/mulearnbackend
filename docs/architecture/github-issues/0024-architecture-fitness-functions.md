# Add the architecture fitness functions

| | |
|---|---|
| ID | 0024 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | M |
| Labels | arch, phase:1, module:platform, type:chore, size:M |
| Depends on | 0014, 0023 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Rules that aren't tests erode. These fitness functions turn three architecture rules into failing checks ([ADR-016](../adr/ADR-016-architecture-enforced-by-automation.md), [04-module-rules.md](../04-module-rules.md#how-ci-enforces-each-rule)).

## Before you start

- Issues 0014 and 0023 must be merged.

## What to do

1. Create `tests/architecture/test_no_cross_module_fk.py`, an AST scan of `modules/*/data/models.py`. A `ForeignKey`, `OneToOneField` or `ManyToManyField` may only point at a model in the same module; references to other modules are id columns.
2. Create `tests/architecture/test_no_migrations.py`, which fails if a `migrations` package exists anywhere in the repository except `api/launchpad/`.
3. Create `tests/architecture/test_hygiene.py`, which bans `print(` and `except Exception: pass` (and bare `except: pass`) in `building_blocks/` and `modules/`.
4. Give each test a clear failure message naming the file, the line and the rule.

## Acceptance criteria

- [ ] All three pass on the current tree.
- [ ] Each fails on a small fixture that breaks its rule. Include those fixtures as test cases.

## How to test

```sh
scripts/test.sh tests/architecture/
```

## Out of scope

- The auth-coverage ratchet (Phase 5).
- The event-payload test (issue 0060).

## Notes for reviewers

Check that each test reads source with `ast` and never imports the module under test.
