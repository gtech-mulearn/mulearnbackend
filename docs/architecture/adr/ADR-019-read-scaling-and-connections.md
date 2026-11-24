# ADR-019: Read scaling: persistent connections, budgets, a proxy and replicas on triggers

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `CONN_MAX_AGE` is 0, so every request opens a new MySQL connection; there is no pooler and no replica.

## Context

Traffic is read-heavy and spiky. Every process that talks to MySQL holds connections, and the sum
across all services must stay below the server's limit. Django's built-in connection pool supports
PostgreSQL and Oracle, not MySQL.

## Options considered

- **`CONN_MAX_AGE` with health checks, plus budgets enforced per service.**
- **ProxySQL:** another component to operate.
- **RDS Proxy from day one:** cost, and pinning on session state.

## Decision

1. **Persistent connections:** `CONN_MAX_AGE=60` and `CONN_HEALTH_CHECKS=True`, under gunicorn
   only ([ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md)).
2. **Connection budgets:**
   - each service has its own MySQL user, with `MAX_USER_CONNECTIONS` set to its budget plus 20%;
   - a budget script checks the inequality in CI and at deploy pre-flight.
3. **Statement time limits per role**, through `max_execution_time` for SELECTs: 5 s for the
   app, 30 s for admin and workers.
4. **RDS Proxy, on a trigger:**
   - Trigger: more than 8 app nodes, or a budget above 60% of `max_connections` with high
     connection churn.
   - Lock-holding roles (the relay and the migration runner) connect directly.
   - Once a proxy is in use, the time limits move from session settings to per-statement hints.
5. **A read replica, on a trigger:**
   - Trigger: primary CPU p95 above 60% at peak for two weeks, or report and admin load above
     20% of the primary.
   - Selectors opt in with `@replica_safe(max_lag_s)`.
   - A read-your-writes pin keeps that caller's reads on the primary for 10 seconds after any
     write. It is a per-user key on the `state` cache alias, not a cookie, so it also covers the
     mobile app.
   - When lag exceeds `max_lag_s`, those reads fall back to the primary.

### Refinements (2026-11-21)

- Per-statement time limits use the `MAX_EXECUTION_TIME` hint from a small helper, kept to about 80 lines; if it grows beyond that, it waits for the slow-query logging in [ADR-012](ADR-012-opentelemetry-sentry-json-logs.md).

## Consequences

- Connection use becomes a number that CI checks.
- Replication lag becomes an explicit, documented property of each read.

## Revisit when

- Each trigger above fires.

## Related ADRs

[ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-009](ADR-009-selective-cqrs-projections.md), [ADR-023](ADR-023-one-image-several-roles.md)
