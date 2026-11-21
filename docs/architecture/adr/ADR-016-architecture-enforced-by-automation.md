# ADR-016: Architecture enforced by automation

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. No workflow under `.github/workflows/` runs tests or architecture checks, and only about 30 of the 91 directories under `api/` have an `__init__.py`.

## Context

Written conventions erode, because not every contributor reads them and review bandwidth is
limited. Legacy code already breaks several rules, so a rule that demands zero violations can't be
switched on at once.

## Options considered

- **Failing CI checks, with ratchet allowlists for legacy debt.**
- **Review guidelines only:** they erode within a semester.

## Decision

Every structural rule is a failing check on pull requests:

- **import-linter** over the complete import graph:
  - Every package under the legacy `api/` tree gets an `__init__.py`, so the graph is complete.
  - Contracts cover layers, module privacy, framework-free domains and the `building_blocks` leaf
    rule.
  - Legacy code (`api`, `utils`, `mu_celery`, `db`) may import only `modules.*.public` and
    `building_blocks.*`.
  - No module imports `db.*`, except its own allowlisted transitional mappings.
- **AST fitness functions** in `tests/architecture/`:
  - no `ForeignKey` to another module's model ([ADR-038](ADR-038-modules-own-their-tables.md));
  - an auth-coverage ratchet ([ADR-007](ADR-007-scoped-grants-and-policies.md));
  - no HTTP clients in views or serializers;
  - bans on `print`, `DEBUG` and `except Exception: pass`.
- **Ratchet allowlists.** A new offender fails, and so does a stale entry, so the lists can only
  shrink.
- **The legacy suite is a ratchet:** its failure set must be a subset of the recorded baseline.
- **Django deprecation warnings are errors** in new code ([ADR-051](ADR-051-toolchain.md)).

### Refinements (2026-11-21)

- `opentelemetry` joins the libraries `domain/` may not import.
- A new module joins `INSTALLED_APPS`, `MIGRATION_MODULES` and a generated import contract (only its `public` and `contracts` importable) in the pull request that creates it.

## Consequences

- Erosion is caught in the pull request that causes it.
- Every exception is visible in a file and shrinks over time.
- Checks must stay fast and deterministic, or contributors route around them.

## Revisit when

- The violation count stops shrinking for two releases.
- The allowlists are empty (switch the ratchets to strict rules).

## Related ADRs

[ADR-007](ADR-007-scoped-grants-and-policies.md), [ADR-017](ADR-017-one-layered-module-structure.md), [ADR-038](ADR-038-modules-own-their-tables.md), [ADR-051](ADR-051-toolchain.md)
