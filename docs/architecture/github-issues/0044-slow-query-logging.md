# Log slow queries with their request id

| | |
|---|---|
| ID | 0044 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | building_blocks |
| Size | S |
| Labels | arch, phase:2, module:building_blocks, type:feature, size:S |
| Depends on | 0018 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Slow queries are the commonest cause of slow pages. Logging every statement over 200 ms with its request id makes them easy to find ([ADR-012](../adr/ADR-012-opentelemetry-sentry-json-logs.md)).

## Before you start

- Issue 0018 must be merged.

## What to do

1. Create `building_blocks/observability/slow_queries.py` with an execute wrapper. It times each statement and logs any over `SLOW_QUERY_MS` (default 200) at WARNING, with the duration, the first 500 characters of the SQL (parameters not included) and the request id.
2. Install it for every request through middleware, using `connection.execute_wrapper`, and for Celery tasks through a task signal.
3. Add a test that runs a deliberately slow SQLite query (`WITH RECURSIVE` counting to a large number) with a low threshold and checks the log record.

## Acceptance criteria

- [ ] Slow statements are logged with the request id and without parameter values.
- [ ] Overhead on a fast query is negligible: show timings in the pull request.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Database-side monitoring (Performance Insights is the maintainers' setup).

## Notes for reviewers

Make sure parameter values are never logged; they can contain personal data.
