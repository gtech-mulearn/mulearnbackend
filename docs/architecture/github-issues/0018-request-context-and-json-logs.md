# Add request ids and JSON logging

| | |
|---|---|
| ID | 0018 |
| Phase / milestone | Phase 1: Foundations |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:1, module:building_blocks, type:feature, size:M |
| Depends on | 0014 |
| Blocks | 0019, 0043, 0044 |
| Repos | mulearnbackend |

## Why

Diagnosing a problem needs every log line of a request tied together, without personal data in the logs ([ADR-012](../adr/ADR-012-opentelemetry-sentry-json-logs.md)).

## Before you start

- Issue 0014 must be merged.
- Read the `LOGGING` block in `mulearnbackend/settings.py`.

## What to do

1. Create `building_blocks/observability/context.py`, with context variables `request_id` and `user_id` and helpers to read them.
2. Create `building_blocks/observability/middleware.py` with `RequestContextMiddleware`:
   - it takes `X-Request-Id` from the request if it matches `^[A-Za-z0-9_-]{8,64}$`; otherwise it generates `req_` plus a UUIDv7 hex string;
   - it sets the context and returns the id in the `X-Request-Id` response header.
3. Create `building_blocks/observability/logging.py` with `JsonFormatter`:
   - it emits `time`, `level`, `logger`, `message`, `request_id`, `user_id` and `trace_id`;
   - it redacts any record attribute or `extra` key named `password`, `token`, `otp`, `email`, `phone` or `muid`.
4. Add the middleware first in `MIDDLEWARE`.
5. Add a `LOG_FORMAT` setting (`text` by default, so nothing changes; `json` selects the formatter).
6. Add tests for the middleware (incoming id kept, bad id replaced, header set) and for redaction.

## Acceptance criteria

- [ ] Every response carries `X-Request-Id`.
- [ ] With `LOG_FORMAT=json`, log lines are JSON with `request_id`.
- [ ] Redacted keys never appear in output.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Tracing (issue 0043).

## Notes for reviewers

Check that the redaction list is applied to `extra` data, not only the message.
