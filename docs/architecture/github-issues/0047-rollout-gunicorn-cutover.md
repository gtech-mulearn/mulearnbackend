# Cut production over to gunicorn

| | |
|---|---|
| ID | 0047 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M, maintainer-only |
| Depends on | 0034, 0038, 0045, 0046, epic:phase-0-security-hardening |
| Blocks | 0105 |
| Repos | mulearnbackend |

## Why

The production cut-over from the development server to gunicorn `gthread` behind nginx, deployed by digest.

## Before you start

- Maintainer-only: it needs production access.
- Issues 0034, 0038, 0045 and 0046 must be merged.
- The Phase 0 security epic must be closed.
- Both load tests must have passed on staging.

## What to do

1. Pick a Tuesday train outside freeze windows. Announce it.
2. Deploy the gunicorn image to production with `scripts/deploy.sh production <digest>`, canary node first.
3. Watch the first hour: connections, error rate, p95 of the top 20 routes, worker restarts.
4. Keep the previous digest for at least two weeks.
5. After one clean week, set `CONN_MAX_AGE=60` and redeploy.

## Acceptance criteria

- [ ] 24 hours after the cut-over:
  - MySQL connections are within the budget and flat (±10%);
  - every 5xx response is the JSON envelope;
  - p95 of the top 20 routes is within 10% of the pre-cut-over baseline.
- [ ] A rollback was possible throughout, and the previous digest is recorded.

## How to test

Record the before/after metrics on the issue.

## Out of scope

- Django 5.2 (issue 0042), which ships in a different train.

## Notes for reviewers

One high-risk change per train: nothing else risky ships in the same release.
