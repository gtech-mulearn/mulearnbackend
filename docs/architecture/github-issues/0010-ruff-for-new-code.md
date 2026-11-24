# Add ruff with checks on new code

| | |
|---|---|
| ID | 0010 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | S |
| Labels | arch, phase:1, module:platform, type:chore, size:S, good first issue |
| Depends on | none |
| Blocks | 0011 |
| Repos | mulearnbackend |

## Why

New code needs one formatter and linter from day one, so reviews spend no time on style. Applying ruff to the whole legacy codebase at once would conflict with every open pull request, so this issue checks new code only ([ADR-051](../adr/ADR-051-toolchain.md)).

## Before you start

- No dependencies.
- There is no `pyproject.toml` or ruff configuration yet.

## What to do

1. Create `requirements-dev.txt` with exact pins for `ruff`, `pytest`, `pytest-django`, `factory_boy`, `hypothesis` and `import-linter`.
2. Create `ruff.toml`:
   - `target-version = "py310"`;
   - `line-length = 120`;
   - lint rules `E`, `F`, `I`, `B` and `UP`;
   - `include = ["building_blocks/**/*.py", "modules/**/*.py", "tests/**/*.py", "scripts/**/*.py"]`, so legacy packages are untouched.
3. Create `.pre-commit-config.yaml` running `ruff check --fix` and `ruff format` on the same paths.

## Acceptance criteria

- [ ] `ruff check` and `ruff format --check` pass on the included paths.
- [ ] No file under `api/`, `db/`, `utils/` or `mu_celery/` is reformatted.
- [ ] `pre-commit run --all-files` touches only included paths.

## How to test

Run `pip install -r requirements-dev.txt`, then `ruff check` and `ruff format --check`, and paste the output.

## Out of scope

- Reformatting legacy code (a later, coordinated maintainer change).
- Type checking (later).

## Notes for reviewers

Check that the `include` list really excludes legacy packages.
