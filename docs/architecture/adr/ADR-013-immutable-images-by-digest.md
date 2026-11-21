# ADR-013: Immutable images, promoted by digest

Status: Accepted (scheduled earlier on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. `.github/workflows/prod-deploy.yml` deploys by SSH, `git pull` and `docker-compose up --build` on the host.

## Context

Building on each host from a `git pull` means different hosts can run different code, nothing is
tested before it runs, and there is no clean rollback.

## Options considered

- **Build once in CI, push to a registry, and promote the same digest.**
- **Build on each host:** not reproducible.

## Decision

- Build the image once in CI and push it to GHCR.
- Deploy the same digest along `dev` → `dev-server` → `staging` → `production`.
- Deploys are rolling and gated on health checks ([ADR-049](ADR-049-deployment-platform-and-dr.md)).
- Rollback means redeploying the previous digest.
- Hotfixes land on `dev` first and are promoted by digest like any other change ([ADR-037](ADR-037-weekly-release-train.md)).

## Consequences

- Releases are reproducible, and every environment runs a known artefact.
- Hosts need registry credentials and a secret store.

## Revisit when

- The platform moves to a container orchestrator (the same principle carries over).

## Related ADRs

[ADR-037](ADR-037-weekly-release-train.md), [ADR-049](ADR-049-deployment-platform-and-dr.md)
