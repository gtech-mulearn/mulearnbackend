# Create the building_blocks package and its import contracts

| | |
|---|---|
| ID | 0014 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M |
| Depends on | 0009, 0011 |
| Blocks | 0015, 0016, 0017, 0018, 0020, 0021, 0022, 0023, 0024, 0027, 0032, 0041 |
| Repos | mulearnbackend |

## Why

Every module and every technical capability needs a home with enforced boundaries. This issue creates the `building_blocks` package and the import contracts that keep it free of business code and legacy imports ([ADR-017](../adr/ADR-017-one-layered-module-structure.md), [04-module-rules.md](../04-module-rules.md)).

## Before you start

- Issues 0009 (packages under `api/`) and 0011 (CI) must be merged.

## What to do

1. Create `building_blocks/__init__.py` and `building_blocks/apps.py` (`BuildingBlocksConfig`), and add `"building_blocks"` to `INSTALLED_APPS`.
2. Create `tests/architecture/module_graph.toml`, with an empty `[modules]` table and a comment explaining how to add a module and its allowed dependencies.
3. Create `scripts/gen_importlinter.py`, which writes `.importlinter` from `module_graph.toml`. For now it emits one contract: `building_blocks` must not import `modules`, `api`, `db`, `utils` or `mu_celery`.
4. Commit the generated `.importlinter`.
5. Add a `lint-imports` step to the `unit` job in `ci.yml`, and add `building_blocks/` to the test paths of the `unit` job (and of the `mysql` job, if issue 0012 has landed).
6. Add `tests/architecture/test_importlinter_generated.py`, which fails if `.importlinter` differs from what the generator produces.

## Acceptance criteria

- [ ] `lint-imports` passes in CI.
- [ ] Adding `import utils` inside `building_blocks` makes `lint-imports` fail (show it on a throwaway branch).
- [ ] The app starts with `building_blocks` installed.

## How to test

```sh
scripts/test.sh tests/architecture/
```

Then run `lint-imports`.

## Out of scope

- Module contracts (issue 0023 extends the generator).

## Notes for reviewers

Check that the generator is deterministic, so the committed `.importlinter` never drifts.
