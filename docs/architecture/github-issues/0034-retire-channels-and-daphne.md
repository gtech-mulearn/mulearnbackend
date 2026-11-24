# Retire Channels and Daphne

| | |
|---|---|
| ID | 0034 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M, core-review |
| Depends on | 0031, 0033 |
| Blocks | 0047 |
| Repos | mulearnbackend |

## Why

Channels and Daphne serve WebSockets that no first-party client uses. They keep the ASGI server in place and add moving parts and attack surface. Retiring them lets the backend run as a plain WSGI app under gunicorn ([ADR-039](../adr/ADR-039-retire-channels-and-daphne.md)).

## Before you start

- Issues 0031 (landing stats over HTTP) and 0033 (gunicorn config) must be merged.
- **A maintainer must first confirm** that the marketing site and any partner don't open these WebSockets. Note the answer in the pull request.

## What to do

1. Remove `"daphne"` and any Channels app from `INSTALLED_APPS`, along with `ASGI_APPLICATION` and `CHANNEL_LAYERS`.
2. Delete `api/routing.py`, `api/common/routing.py`, `api/dashboard/lc/dash_lc_routing.py` and the consumer classes they route to. Keep any non-WebSocket code those files share.
3. In `signals.py` (created in `api/common/` by issue 0030), drop the WebSocket broadcast and keep only the cache invalidations.
4. Remove `channels`, `channels-redis` and `daphne` from `requirements.txt`, and Twisted if nothing else needs it.
5. Make `mulearnbackend/asgi.py` a plain Django ASGI app, or delete it if nothing uses it.
6. Change `entrypoint.sh` to start gunicorn. The deployed environments keep their current command until the cut-over issue.

## Acceptance criteria

- [ ] `grep -ri "channels\|daphne" requirements.txt mulearnbackend/` finds nothing.
- [ ] The test suite passes on both tiers.
- [ ] `python manage.py check` passes.
- [ ] The landing-statistics HTTP endpoint still works.
- [ ] Staging has run one full release train with this change before production gets it.

## How to test

```sh
scripts/test.sh api/common/tests/
```

## Out of scope

- Production deploys (issue 0047).

## Notes for reviewers

Check that no import of `channels` survives anywhere, including inside functions.

This changes what production runs until the gunicorn cut-over (issue 0047). Without `daphne` in `INSTALLED_APPS`, `runserver` is Django's own development server instead of Daphne's. Two reviewers; a maintainer holds it back from production until staging has run one full train with it.
