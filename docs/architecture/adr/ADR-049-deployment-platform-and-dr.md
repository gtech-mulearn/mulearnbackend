# ADR-049: Deployment platform, region and disaster recovery

Status: Accepted (new on 2026-11-21; refines ADR-013 and ADR-023)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. Production runs `docker-compose` on a host that is updated with `git pull`.

## Context

The team is small and volunteer, and the budget is limited. Deploys must be rolling, gated on
health checks, and reversible. Recovery targets must be explicit and tested.

## Options considered

- **Docker Compose on EC2, with a real rolling deploy.**
- **ECS on Fargate now.**
- **Kubernetes (EKS).**

## Decision

**Docker Compose on EC2, now:**
- Images are pulled by digest from GHCR, with nginx on each node.
- `deploy.sh <env> <digest>`:
  1. Pre-flight: the config check, the connection budget and the required schema ids.
  2. Then, node by node, canary first: drain → stop → start → readiness → next node.
- Roles run as compose services ([ADR-023](ADR-023-one-image-several-roles.md)). Beat runs on one node only.

**ECS on Fargate on a trigger:** four or more app nodes, autoscaling needed for national events, or
more than one day a month of host operations. The roles map to ECS services one to one.

**Kubernetes is not planned.** Its trigger is five or more independently deployed services owned
by separate teams.

**Region and disaster recovery:**
- An Indian AWS region, with RDS Multi-AZ.
- Automated backups for 14 days with point-in-time recovery, plus a daily snapshot copy to a
  second Indian region.
- **A quarterly restore drill:** restore to a scratch instance, run the parity and reconciliation
  checks, and record the time taken.
- **Targets:**
  - in-region: RPO ≤ 5 minutes, RTO ≤ 2 hours;
  - loss of a whole region: RPO ≤ 24 hours, RTO ≤ 24 hours. This is an accepted risk.
- Cost budget alarms.

### Refinements (2026-11-21)

- Deploy pre-flight checks that every alter id in `schema/REQUIRED` has been applied, the applied-set check of [ADR-040](ADR-040-db-scripts-safety-net.md); `db.version` is for display only.

## Consequences

- Low operating cost, and a path to ECS without redesign.

## Revisit when

- Each trigger above fires.

## Related ADRs

[ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-013](ADR-013-immutable-images-by-digest.md), [ADR-023](ADR-023-one-image-several-roles.md), [ADR-040](ADR-040-db-scripts-safety-net.md), [ADR-048](ADR-048-typed-configuration.md)
