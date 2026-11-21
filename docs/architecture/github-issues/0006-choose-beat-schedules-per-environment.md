# Let each environment choose which beat schedules run

| | |
|---|---|
| ID | 0006 |
| Phase / milestone | Phase 0: Stabilise and secure |
| Module | platform |
| Size | S |
| Labels | arch, phase:0, module:platform, type:feature, size:S, good first issue |
| Depends on | none |
| Blocks | none |
| Repos | mulearnbackend |

## Why

`CELERY_BEAT_SCHEDULE` in `mulearnbackend/settings.py` has 14 entries: intern, alumni, mentorship, job expiry, event status, organisation and learning-circle aggregates, leaderboards and push. Some have never run in production. Promoting them all at once would run months of backlog on production data the first time beat starts. Each environment should choose which schedules run ([ADR-042](../adr/ADR-042-background-work-celery.md)).

## Before you start

- Set up your clone as [Setting up a fresh clone](README.md#setting-up-a-fresh-clone) describes.
- Read the `CELERY_BEAT_SCHEDULE` block at the end of `mulearnbackend/settings.py` and the `celery-beat` service in `docker-compose.yml`.

## What to do

1. Add a setting `BEAT_SCHEDULES`, read from the environment with `decouple`, default `"all"`. Parse it like this:
   - trim it, and compare the keywords case-insensitively;
   - unset or empty means `all`;
   - `all` and `none` are valid only on their own;
   - anything else is a comma-separated list of schedule names (the dictionary keys of `CELERY_BEAT_SCHEDULE`). Spaces around names and empty items, such as a trailing comma, are ignored, and a repeated name counts once;
   - any unknown name is an error.
2. Create `mulearnbackend/celery_schedules.py` with a pure function `select_schedules(schedule: dict, selection: str) -> dict`. It returns a new dictionary with the chosen entries, and raises `django.core.exceptions.ImproperlyConfigured` naming every unknown schedule.
3. Rebind `CELERY_BEAT_SCHEDULE = select_schedules(CELERY_BEAT_SCHEDULE, BEAT_SCHEDULES)` at the end of the settings, after the schedule block.
4. Document `BEAT_SCHEDULES` in a comment next to the schedule block, and add it, commented out, to `.env.sample`.
5. Add `tests/test_celery_schedules.py` (create `tests/` if issue 0001 hasn't yet) with these cases:
   - `all`, `ALL` and an empty string return every entry;
   - `none` returns none;
   - a list returns exactly those entries, ignoring spaces, a trailing comma and repeats;
   - an unknown name raises, naming it;
   - `all` or `none` combined with a name raises.

## Acceptance criteria

- [ ] With no `BEAT_SCHEDULES` set, the schedule is exactly as today: the second command below prints all 14 names.
- [ ] With `BEAT_SCHEDULES=none`, the same command prints `[]`, so beat starts with no schedules.
- [ ] An unknown name fails at startup with a message naming it.

## How to test

```sh
DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" DATABASE_USER= DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT= python -m pytest tests/test_celery_schedules.py --import-mode=importlib
```

To check the settings themselves:

```sh
BEAT_SCHEDULES=none DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" DATABASE_USER= DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT= python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings'); django.setup(); from django.conf import settings; print(sorted(settings.CELERY_BEAT_SCHEDULE))"
```

Expect `[]`. Run it again without `BEAT_SCHEDULES=none` and expect the 14 names.

## Out of scope

- Choosing the production list (a maintainer sets it when deploying).
- Schedule claims and heartbeats (issue 0067).

## Notes for reviewers

- The default must keep today's behaviour, so dev keeps running every schedule.
- An unknown name stops every process at startup, not only beat, because they all share the settings. That is intended: a typo must never silently turn schedules off.
- This is a stopgap. [ADR-042](../adr/ADR-042-background-work-celery.md) enables schedules one at a time behind flags, off by default in production, once the flag store (issue 0074) and `@scheduled` (issue 0067) exist. `BEAT_SCHEDULES` chooses which schedules a deployment registers. It is deployment configuration, not a feature switch, so it doesn't break the rule that feature switches aren't environment variables.
- Production's value must be set explicitly before the next promotion. Say so in the pull request, so the release notes carry it.
