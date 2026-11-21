# ADR-051: Toolchain

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started.

## Context

Formatting is pinned to an old black release. There is no type checking, and the test setup can't
build a schema. Contributors change every semester, so tools must be standard and run the same
locally as in CI.

## Options considered

- **A standard Python toolchain, configured once and run through pre-commit and CI.**
- **Keep black and add tools one at a time:** more configuration surface, and drift.

## Decision

| Tool | Rule |
|---|---|
| ruff | Lint and format, replacing black. One mechanical format commit, which also normalises line endings. |
| mypy + django-stubs + djangorestframework-stubs | Strict on `building_blocks/` and `modules/`; legacy code excluded. Pin stub versions compatible with the current Python until the upgrade. |
| import-linter | Over the complete import graph ([ADR-016](ADR-016-architecture-enforced-by-automation.md)). |
| pytest | pytest-django, factory_boy and hypothesis (ledger invariants). Two database tiers ([ADR-040](ADR-040-db-scripts-safety-net.md)). |
| Coverage | `diff-cover` ≥ 80% on changed lines in `modules/` and `building_blocks/`; a ratchet for legacy code. |
| Warnings | Django removal warnings are errors in `building_blocks/`, `modules/` and `tests/`. The legacy suite reports a warning count that may only fall. |
| Security scanning | gitleaks (including history), pip-audit for dependencies, and Trivy for images. |
| pre-commit | The same hooks run locally. |

## Consequences

- One formatter and one linter, and type safety where new code lives.
- A one-time format churn commit.

## Revisit when

- A tool is abandoned upstream, or CI time becomes a bottleneck.

## Related ADRs

[ADR-016](ADR-016-architecture-enforced-by-automation.md), [ADR-040](ADR-040-db-scripts-safety-net.md), [ADR-050](ADR-050-platform-versions.md)
