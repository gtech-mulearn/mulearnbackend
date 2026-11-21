# Declare required schema ids and refuse to start without them

| | |
|---|---|
| ID | 0052 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | M |
| Labels | arch, phase:3, module:platform, type:feature, size:M, core-review |
| Depends on | 0020, 0032, 0049 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Code must never run ahead of its schema. If a release needs an alter that hasn't been applied, every container crash-loops on missing columns. Declaring the alters a release needs, and checking them at deploy and boot, stops that ([ADR-040](../adr/ADR-040-db-scripts-safety-net.md)).

## Before you start

- Issues 0032 (health) and 0049 (alter ids) must be merged.
- Issue 0020 must also be merged.

## What to do

1. Create `schema/REQUIRED`, one alter id per line: the alters this code needs. Start with the ids already applied everywhere.
2. Create `building_blocks/health/schema.py` with `missing_schema_ids() -> list[str]`. It reads `schema_migration` (read-only) and returns the required ids that aren't applied. If the table doesn't exist yet, it returns an empty list and logs a warning.
3. Call it in `config_check` and from the container entrypoint before the server starts. Never call it from `ready()`, which must not query the database ([ADR-048](../adr/ADR-048-typed-configuration.md)):
   - with `SCHEMA_CHECK=enforce`, a missing id refuses to boot or deploy with a clear message;
   - with `SCHEMA_CHECK=warn` (the default until the runner is on production), it only logs.
4. Readiness does not check the schema.
5. Add tests with a fake `schema_migration` result.

## Acceptance criteria

- [ ] With `SCHEMA_CHECK=enforce` and a missing id, boot fails, naming the id.
- [ ] With `warn`, boot succeeds and logs.
- [ ] `config_check` reports missing ids.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Turning on `enforce` in production (after issue 0051).

## Notes for reviewers

Check that a database without the `schema_migration` table never stops boot in `warn` mode.
