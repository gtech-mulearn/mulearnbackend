# Add the business clock with IST period bounds

| | |
|---|---|
| ID | 0016 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:S |
| Depends on | 0014 |
| Blocks | 0085 |
| Repos | mulearnbackend |

## Why

Data is stored in UTC, but μLearn runs on Indian Standard Time: midnight IST is 18:30 UTC the day before. Monthly boundaries computed naively in UTC put awards in the wrong month ([ADR-053](../adr/ADR-053-business-calendar-and-money.md)).

## Before you start

- Issue 0014 must be merged.

## What to do

1. Create `building_blocks/clock.py` with:
   - `now() -> datetime`, an aware UTC datetime;
   - `BUSINESS_TZ = ZoneInfo("Asia/Kolkata")`;
   - `period_bounds(kind: str, at: datetime, tz=BUSINESS_TZ) -> tuple[datetime, datetime]` for `day`, `week` (weeks start on Monday) and `month` and `year`. It returns half-open UTC bounds `[start, end)`;
   - `period_key(at: datetime) -> str`, the IST month as `YYYY-MM`.
2. Add `tzdata` to `requirements.txt` if it is missing, so `zoneinfo` works on Windows.
3. Add `building_blocks/tests/test_clock.py`:
   - 18:29 UTC on 31 Jan is still January IST, and 18:30 UTC is February;
   - the December → January roll;
   - week bounds start on Monday 00:00 IST;
   - a naive datetime raises.

## Acceptance criteria

- [ ] All tests pass, including on Windows.
- [ ] No other module computes business periods. Later issues use this one.

## How to test

```sh
scripts/test.sh building_blocks/tests/test_clock.py
```

## Out of scope

- Fixing existing period queries (they move as their modules move).

## Notes for reviewers

Check the half-open bounds and the Monday week start.
