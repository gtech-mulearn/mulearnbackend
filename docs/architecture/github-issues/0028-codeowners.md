# Add a CODEOWNERS file

| | |
|---|---|
| ID | 0028 |
| Phase / milestone | Phase 1: Foundations |
| Module | platform |
| Size | S |
| Labels | arch, phase:1, module:platform, type:chore, size:S, maintainer-only |
| Depends on | none |
| Blocks | 0029 |
| Repos | mulearnbackend |

## Why

Reviews should go to the people who own each area automatically. `core-review` paths need a maintainer ([16-contributing-to-the-architecture.md](../16-contributing-to-the-architecture.md#reviews)).

## Before you start

- Maintainer-only: the maintainers choose the teams.

## What to do

1. Create `.github/CODEOWNERS` with entries for:
   - `/building_blocks/`, `/building_blocks/authz/` and `/building_blocks/messaging/`;
   - `/modules/contributions/` and `/modules/identity_access/`;
   - `/docs/architecture/`;
   - `/.github/workflows/`;
   - `/schema/`.
   Use team placeholders of the form `@gtech-mulearn/<team>`.
2. Replace the placeholders with real teams, creating them if needed.

## Acceptance criteria

- [ ] A pull request touching `building_blocks/authz/` requests the right team automatically.
- [ ] Every path in the list has an owner.

## How to test

Open a draft pull request touching one file in each listed path and check the requested reviewers.

## Out of scope

- Branch rules (issue 0029).

## Notes for reviewers

Team names are the maintainers' choice.
