# Keep the beat schedule file on a volume

| | |
|---|---|
| ID | 0068 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S |
| Depends on | 0004, 0037, 0064 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Beat stores its schedule state in a file. Today that file lives in `/tmp` (`--schedule /tmp/celerybeat-schedule`), so a container restart loses it.

## Before you start

- Issue 0064 must be merged.
- Issues 0004 and 0037 must also be merged.

## What to do

1. In `docker-compose.local.yml` and the deploy compose file, mount a named volume at `/data` for the beat service, and start it with `--schedule /data/celerybeat-schedule`.
2. Add a comment explaining that exactly one beat may run per deployment.

## Acceptance criteria

- [ ] Restarting the beat container keeps the schedule file.

## How to test

Restart beat locally and confirm the file persists in the volume.

## Out of scope

- Slot claims (issue 0067).

## Notes for reviewers

This is a small change; check that both compose files are updated.
