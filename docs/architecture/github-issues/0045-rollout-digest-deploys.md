# Roll out digest deploys to dev-server and staging

| | |
|---|---|
| ID | 0045 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | S |
| Labels | arch, phase:2, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0037 |
| Blocks | 0047 |
| Repos | mulearnbackend |

## Why

Before production, the digest deploy and its rollback must be proven on the shared environments.

## Before you start

- Maintainer-only: it needs host access.
- Issue 0037 must be merged.

## What to do

1. Install Docker Compose v2 and GHCR credentials on the `dev-server` and `staging` hosts.
2. Fill in `deploy/dev-server/nodes.txt` and `deploy/staging/nodes.txt`.
3. Switch their deploy workflows to `scripts/deploy.sh <env> <digest>`, using the digest from the image workflow.
4. Rehearse a deploy and a rollback on staging, and record the timings on the issue.

## Acceptance criteria

- [ ] `dev-server` and `staging` deploy by digest from CI.
- [ ] The staging rollback rehearsal finishes within 5 minutes.

## How to test

Do the rehearsal on staging and record the timings.

## Out of scope

- Production (issue 0047).

## Notes for reviewers

Check that the old host-build path is fully disabled for these environments.
