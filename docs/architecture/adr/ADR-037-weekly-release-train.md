# ADR-037: Weekly release train with flag-driven releases

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The branches `dev`, `dev-server`, `staging` and `production` each deploy through their own workflow in `.github/workflows/`.

## Context

A national platform with volunteer maintainers needs a predictable, low-ceremony cadence that
separates deploying from releasing.

## Options considered

- **A weekly train with features released by flags.**
- **Ad-hoc deploys:** unpredictable and hard to roll back.
- **Continuous deployment:** needs more test and observability maturity than exists today.

## Decision

- Two-week sprints, Thursday to Wednesday.
- **A weekly production train on Tuesday,** moving to Wednesday on holidays:
  1. a Friday release candidate;
  2. a weekend soak on staging;
  3. a Monday go/no-go.
- Features ship dark and are released by audited flag rollouts ([ADR-031](ADR-031-feature-flags.md)).
- **Freeze and caution windows:** the year end, the exam season and national events.
- **Branch protection** on `dev`, `staging` and `production`:
  - at least one review;
  - two reviews for authentication, authorization, ledger and payment paths. CODEOWNERS
    requests the right teams, and a required `two-reviewers` check counts the approvals,
    because one code-owner approval alone satisfies CODEOWNERS.
- **Hotfixes** land on `dev` first and are promoted by digest ([ADR-013](ADR-013-immutable-images-by-digest.md)). No feature branch
  merges straight into `production`.
- `staging` has a deploy workflow.

## Consequences

- Small, frequent, reversible changes, and a predictable community calendar.
- The train needs a rotating release manager.

## Revisit when

- Test and observability maturity support continuous deployment.

## Related ADRs

[ADR-013](ADR-013-immutable-images-by-digest.md), [ADR-031](ADR-031-feature-flags.md), [ADR-049](ADR-049-deployment-platform-and-dr.md)
