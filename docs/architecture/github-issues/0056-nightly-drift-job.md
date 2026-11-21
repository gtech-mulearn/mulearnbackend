# Run the schema drift report nightly against production

| | |
|---|---|
| ID | 0056 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0055 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Schema drift on production should be found the next morning, not in the next release.

## Before you start

- Maintainer-only: it needs production access.
- Issue 0055 must be merged.

## What to do

1. Create a read-only MySQL user for the drift job.
2. Run `manage.py schema_drift --format json` nightly against production as that user.
3. Post differences to the ops channel, and open a ticket when a new difference appears.

## Acceptance criteria

- [ ] The job runs nightly, and its output is visible to maintainers.
- [ ] A new difference produces a ticket within a day.

## How to test

Run the job manually once and paste the (empty) result.

## Out of scope

- Fixing what it finds.

## Notes for reviewers

The user must have no write privileges.
