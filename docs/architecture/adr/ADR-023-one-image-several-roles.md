# ADR-023: One image, several deployment roles (phased)

Status: Accepted (amended on 2026-11-21: phased)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `docker-compose.yml` runs one web container, one Celery worker and one beat.

## Context

Anonymous, learner, admin, bot and partner traffic differ in cost, criticality and scaling signal.
Current traffic doesn't justify four API pools on day one.

## Options considered

- **One image deployed as several roles, introduced in phases.**
- **Four API pools now:** more target groups and dashboards than today's load needs.
- **Separate services per audience:** microservices by another name.

## Decision

| Phase | Roles |
|---|---|
| Now | `web` (one gthread pool); `worker-fast` (`critical`, `default`, `projections`); `worker-notify`; `worker-bulk` (`bulk`, `integrations`); `beat` (exactly one); `relay` |
| When the bot calls the API | Add `web-internal` for `/api/v1/internal/*`, so a bot or partner storm can't starve learners |
| On [ADR-019](ADR-019-read-scaling-and-connections.md)'s triggers | Add `web-admin` (replica-routed, shed first) and `web-public` (cached) |

The load balancer routes by path. Each role has its own pool, timeouts and connection budget.

## Consequences

- Runtime bulkheads without microservices.
- The connection budget counts every role ([ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md)).

## Revisit when

- Each phase's trigger fires.

## Related ADRs

[ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-019](ADR-019-read-scaling-and-connections.md), [ADR-042](ADR-042-background-work-celery.md), [ADR-049](ADR-049-deployment-platform-and-dr.md)
