# ADR-012: OpenTelemetry, Sentry and JSON logs

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. There is no OpenTelemetry or Sentry in `requirements.txt`; logs are plain Django logging.

## Context

Diagnosing a production problem needs correlated logs, metrics and traces at a cost an
open-source project can afford. India's CERT-In directions require 180 days of logs kept in
India, and observability vendors become data processors under privacy law.

## Options considered

- **OpenTelemetry SDK → collector → a managed Grafana stack, plus Sentry for errors.**
- **A self-hosted LGTM stack:** no third-party processors, but the team runs it.
- **SigNoz:** an all-in-one stack, but less familiar to contributors.

## Decision

- **Logs of record:** CloudWatch Logs in the production region, kept 400 days in ap-south-1. That
  covers the 180 days CERT-In requires and the one year the DPDP Rules require for certain logs;
  counsel may shorten it.
- **Metrics and traces:** OTel SDK → collector → Grafana Cloud.
- **Errors:** Sentry, with `send_default_pii=False` and a redaction filter.
- **Minimise what processors receive.** Grafana and Sentry receive no personal data:
  - no user identifiers as metric labels;
  - traces drop request bodies and query strings.
- **Logs** are JSON and carry `request_id` and the user UUID. People-facing identifiers such as
  muid are not logged.
- **Slow queries:** the RDS slow log and Performance Insights, plus a Django `execute_wrapper`
  that logs statements over 200 ms with the request id.
- **Tail sampling in the collector:** 5% of normal traces, and 100% of errors and slow requests.
- OTel instrumentation packages are pinned.

### Refinements (2026-11-21)

- Logs carry `request_id`, the user's UUID and `trace_id`. `muid` is never logged; an audited lookup from muid to UUID serves investigations.

## Consequences

- Vendor-neutral instrumentation at low cost.
- Every processor appears in the privacy processor inventory ([ADR-052](ADR-052-privacy-minors-erasure.md)).
- If counsel rejects foreign processors, fall back to the self-hosted stack.

## Revisit when

- Free-tier limits are exceeded, or residency advice changes.

## Related ADRs

[ADR-033](ADR-033-slos-and-burn-rate-alerts.md), [ADR-052](ADR-052-privacy-minors-erasure.md)
