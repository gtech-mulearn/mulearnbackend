# Add UUIDv7 id helpers

| | |
|---|---|
| ID | 0015 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:S |
| Depends on | 0014 |
| Blocks | 0059 |
| Repos | mulearnbackend |

## Why

New rows get time-ordered ids, so inserts into new append-heavy tables stay index-friendly ([ADR-015](../adr/ADR-015-uuid-keys-and-public-ids.md)). Python 3.10 has no built-in UUIDv7.

## Before you start

- Issue 0014 must be merged.

## What to do

1. Create `building_blocks/ids.py` with:
   - `uuid7() -> uuid.UUID`: RFC 9562 version 7, with a 48-bit Unix millisecond timestamp and a counter, so ids generated in the same millisecond are still increasing within one process;
   - `uuid7_str() -> str`: the canonical 36-character form.
2. Add `building_blocks/tests/test_ids.py`:
   - the version nibble is 7 and the variant is RFC 4122;
   - 10,000 ids from one process are strictly increasing;
   - the string length is 36.

## Acceptance criteria

- [ ] All tests pass.
- [ ] The module imports only the standard library.

## How to test

```sh
scripts/test.sh building_blocks/tests/test_ids.py
```

## Out of scope

- Changing existing keys.

## Notes for reviewers

Check the bit layout against RFC 9562 section 5.7.
