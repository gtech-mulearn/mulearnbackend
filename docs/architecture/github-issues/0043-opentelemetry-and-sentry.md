# Wire up OpenTelemetry and Sentry

| | |
|---|---|
| ID | 0043 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:2, module:building_blocks, type:feature, size:M |
| Depends on | 0018, 0020 |
| Blocks | 0048 |
| Repos | mulearnbackend |

## Why

There is no tracing or error tracking today. OpenTelemetry for traces and metrics, and Sentry for errors with no personal data, make production problems diagnosable ([ADR-012](../adr/ADR-012-opentelemetry-sentry-json-logs.md), [11-reliability-and-observability.md](../11-reliability-and-observability.md)).

## Before you start

- Issues 0018 (request context) and 0020 (typed config) must be merged.

## What to do

1. Add pinned `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-instrumentation-django`, `-celery`, `-redis` and `sentry-sdk` to `requirements.txt`.
2. Create `building_blocks/observability/otel.py` with `setup(role: str)`, as in the example in 11-reliability-and-observability.md:
   - service name `mulearnbackend`, plus resource attributes for the environment and role;
   - the request hook drops query strings;
   - it does nothing unless `OTEL_ENABLED` is true.
3. Create `building_blocks/observability/sentry.py` with `setup()`: `send_default_pii=False`, a `before_send` that removes request bodies, cookies and any key from the redaction list, and the `release` set to the image tag. It does nothing unless `SENTRY_DSN` is set.
4. Call both from `wsgi.py` and the Celery app setup.
5. Add `trace_id` to the JSON log formatter when a span is active.

## Acceptance criteria

- [ ] With `OTEL_ENABLED=true` and a local collector, a request produces a trace with the Django and database spans.
- [ ] With `SENTRY_DSN` set to a test project, an error event contains no body, cookie or redacted key.
- [ ] With neither set, nothing changes.

## How to test

```sh
scripts/test.sh building_blocks/tests/
```

## Out of scope

- Dashboards and alerts (issue 0048).

## Notes for reviewers

Check the scrubbing: no personal data may reach a processor.
