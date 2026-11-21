# ADR-025: Serving-model evolution

Status: Superseded by ADR-006 (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: superseded; see ADR-006.

## Context

The 2026-11-17 plan started with sync gunicorn workers and moved to threaded workers later. The code already runs each
request on its own thread, so the reason for starting with sync workers no longer applies, and
sync workers would cut concurrency where campus bursts land.

## Options considered

- **Sync workers first, threads later** (the 2026-11-17 decision).
- **`gthread` from day one** (adopted in [ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md)).

## Decision

- Use `gthread` from the cut-over ([ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md)).
- The only staged part left is raising threads per worker beyond 4. That step is gated on every
  outbound call having a timeout, and on a load test.

## Consequences

- No intermediate capacity regression.

## Revisit when

- See [ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md).

## Related ADRs

[ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-019](ADR-019-read-scaling-and-connections.md)
