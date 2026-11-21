# Add typed configuration and config_check

| | |
|---|---|
| ID | 0020 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:L |
| Depends on | 0005, 0014 |
| Blocks | 0022, 0037, 0043, 0052, 0071 |
| Repos | mulearnbackend |

## Why

Settings are read at import with `decouple_config`, some without defaults and some with the wrong type. For example, `EMAIL_USE_TLS` is read without `cast=bool`, so `"False"` is truthy. Typed, declared settings, checked before deploy, turn crash-loops and silent misconfiguration into a pre-flight error ([ADR-048](../adr/ADR-048-typed-configuration.md)).

## Before you start

- Issues 0005 (required settings) and 0014 must be merged.

## What to do

1. Create `building_blocks/config.py`:
   - `Setting(name, type, default=None, required_in=frozenset(), secret=False)`;
   - `declare(*settings)`;
   - `get(name)`;
   - parsing for `str`, `int`, `bool` (accepting `true/false/1/0/yes/no`, case-insensitive), `list[str]` (comma-separated) and URLs.
2. Declare every setting `mulearnbackend/settings.py` reads, with its type and the environments that require it (`MULEARN_ENV` is one of `local`, `dev`, `staging`, `production`). Replace the reads with `config.get(...)`, and remove the `_required` helper from 0005.
3. Create `building_blocks/management/commands/config_check.py` (`manage.py config_check --env-file <path>`). It validates every declared setting for that file's `MULEARN_ENV`, prints problems without printing secret values, and exits 1 on any problem.
4. Add tests: bool parsing (including `"False"`), a missing required value, a value that is required only in production, and secrets never printed.

## Acceptance criteria

- [ ] With a complete environment, the app behaves exactly as before, except that `EMAIL_USE_TLS="False"` is now false (a named fix in the pull request description).
- [ ] `config_check` reports every problem in one run.
- [ ] No secret value appears in any output.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Moving secrets into a secret store (a maintainer task).

## Notes for reviewers

The `EMAIL_USE_TLS` change is deliberate. Make sure it is called out for the release notes.
