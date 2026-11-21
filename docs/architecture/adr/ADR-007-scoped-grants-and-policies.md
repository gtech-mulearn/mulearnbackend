# ADR-007: Scoped grants and resource-aware policies

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Views check roles through `utils/permission.py`.

## Context

Users hold several roles at once, for example learner, mentor, campus lead and enabler, and each
role has its own verification. A single "the role" check is wrong. Access rules scattered as
role-name string checks are hard to test and easy to get wrong.

## Options considered

- **Custom grants and policies in `building_blocks.authz`.**
- **django-rules:** a second rule model alongside the policy registry.
- **django-guardian:** per-object permission tables that don't fit scoped roles.

## Decision

- A caller is a `Principal` holding `Grant`s `(role, scope_type, scope_id, status)`.
  - Only verified grants authorize anything.
  - Scope types are `global`, `state`, `district`, `campus`, `ig`, `lc` and `chapter_path`.
  - Chapters match by materialised-path prefix ([ADR-028](ADR-028-chapter-materialised-paths.md)).
- **A decision is the union of per-grant decisions:**
  `allowed(p, action, r) = any(policy(action, g, r) for g in verified_grants(p))`.
  - No policy may read more than one grant.
  - A property test checks, for random grant sets, that a set allows exactly what its
    individual grants allow. A combination of roles therefore never grants more than its
    parts.
  - A rule that genuinely needs two grants together requires its own ADR.
- **Every role is classified in the catalogue** as privileged or not. Privileged roles authorize
  only once verified.
- **Default deny:**
  - `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`.
  - Public endpoints opt out with `PublicAPIView`, each listed with a reason.
  - Existing views that are meant to be public are marked explicitly before the default changes,
    so no behaviour changes.
  - An auth-coverage ratchet blocks any new implicitly public view.
- **The grant cache is invalidated on commit.** Grant changes publish `GrantChanged`.
- Admin actions write `audit_event` ([ADR-032](ADR-032-audit-trail-and-retention.md)).
- **Test matrix:** roles × actions × scope relations, generated from the policy table, plus the
  property test above.

### Refinements (2026-11-21)

- `MuLearnAPIView` sets `request.principal` (through `principal_of()`) before DRF runs permission classes, so a permission class that reads grants sees them.
- Scheduled jobs act as a named system principal, `system_principal("<module>.<job>")`, whose id is `system:<job>`. Policies grant it nothing, so job commands call no `require()`, and their writes are audited with `actor_kind = system`. Only tasks and management commands may create one.

## Consequences

- One place decides access, and it is testable without HTTP.
- Moving legacy endpoints onto policies is incremental, with one switch per step.
- Grant changes must always go through `identity_access` commands, so invalidation happens.

## Revisit when

- Someone proposes a policy that reads more than one grant.

## Related ADRs

[ADR-016](ADR-016-architecture-enforced-by-automation.md), [ADR-028](ADR-028-chapter-materialised-paths.md), [ADR-032](ADR-032-audit-trail-and-retention.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
