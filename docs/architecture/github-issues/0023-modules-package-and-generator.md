# Add the modules package and the new_module generator

| | |
|---|---|
| ID | 0023 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:L, core-review |
| Depends on | 0014 |
| Blocks | 0024, 0081, 0101 |
| Repos | mulearnbackend |

## Why

Every module must have the same layout, so contributors learn one shape. A generator makes the layout free to get right ([ADR-017](../adr/ADR-017-one-layered-module-structure.md), [04-module-rules.md](../04-module-rules.md#the-anatomy-of-a-module)).

## Before you start

- Issue 0014 must be merged.

## What to do

1. Create `modules/__init__.py`, `modules/urls.py` (empty `urlpatterns`) and `modules/internal_urls.py`.
2. Mount `modules.urls` under `/api/v1/`, **after** the existing includes in `api/urls.py`, so no legacy route is shadowed.
3. Create `building_blocks/management/commands/new_module.py` (`manage.py new_module <name> [--root <dir>]`). It creates the layout from the module-rules page:
   - `apps.py`, `public.py`, `contracts.py`, `policies.py`, `tasks.py`;
   - `api/`, `services/`, `selectors/`, `data/`, `adapters/`, `domain/`;
   - `management/commands/`, and `tests/` with `domain/`, `services/`, `selectors/`, `api/` and `mysql/`.

   It also creates `docs/architecture/modules/<name>.md` from a template, if that page doesn't exist. It never edits shared files.
4. The generator refuses a name that isn't in the module catalogue in `docs/architecture/modules/README.md`.
5. Add tests that run the generator into a temporary `--root` and check the tree.
6. Extend `scripts/gen_importlinter.py` (issue 0014) to emit, for every module listed in `module_graph.toml`:
   - a layers contract, in the order [Layers and imports](../04-module-rules.md#layers-and-imports) gives: `api` and `tasks`, then `services`, then `selectors`, then `data` and `adapters`, then `domain`;
   - a forbidden contract that keeps `domain` free of Django, DRF, Celery, HTTP clients and `building_blocks.persistence`, `.messaging`, `.http` and `.cache`;
   - an independence contract: another module is imported only through its `public` and `contracts`, and only when `module_graph.toml` lists that dependency.

   It also emits one contract for legacy code: `api`, `db`, `utils` and `mu_celery` may import only `modules.*.public`, `modules.*.contracts` and `building_blocks`.
7. Add `tests/architecture/test_module_graph.py`: the graph is acyclic, every package under `modules/` is declared in it, and every declared module exists.
8. Add `modules/` to the test paths of the `unit` and `mysql` jobs in `ci.yml`.

## Acceptance criteria

- [ ] `manage.py new_module events --root /tmp/x` creates the expected tree.
- [ ] An unknown name is refused.
- [ ] On a throwaway branch, a module that imports another module's `services` fails `lint-imports`.
- [ ] `test_module_graph.py` fails for a cycle and for an undeclared module.
- [ ] No legacy route changes: compare `show_urls`-style output, or the URL resolver, before and after.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Creating any real module (each module's first issue does that).

## Notes for reviewers

Check the URL mount order, so no legacy route can be shadowed.
