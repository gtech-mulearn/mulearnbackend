# Protect dev, staging and production with review rules

| | |
|---|---|
| ID | 0029 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | S |
| Labels | arch, phase:1, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0011, 0028 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Review rules only hold if GitHub enforces them. `dev`, `staging` and `production` need required checks and reviews ([ADR-037](../adr/ADR-037-weekly-release-train.md)).

## Before you start

- Maintainer-only: it needs repository admin rights.
- Issues 0011 and 0028 must be merged.

## What to do

1. Add rulesets for `dev`, `staging` and `production`:
   - pull request required;
   - at least 1 approval;
   - required checks `ci / unit` (and `ci / mysql` once 0012 lands);
   - no force pushes and no deletions.
2. Add `.github/workflows/two-reviewers.yml`. It fails when a pull request touches a `core-review` path (`building_blocks/authz/`, `building_blocks/messaging/`, `modules/contributions/`, `modules/identity_access/`, `scripts/deploy.sh`, `.github/workflows/`) with fewer than 2 approvals. Make it a required check.
3. Document the rules in `CONTRIBUTING.md`.

## Acceptance criteria

- [ ] A pull request into `dev` can't merge without a passing `ci / unit` and an approval.
- [ ] A pull request touching `building_blocks/authz/` can't merge with one approval.

## How to test

Open a test pull request touching a core path, and confirm the merge button stays blocked until two approvals.

## Out of scope

- Changing who the maintainers are.

## Notes for reviewers

Make sure maintainers can still merge urgent fixes through the same rules, not by bypassing them.
