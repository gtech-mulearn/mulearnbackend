# ADR-050: Platform versions and upgrade cadence

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. The backend runs Django 4.2.7 on `python:3.10-slim-buster`.

## Context

- Django 4.2's support ended in April 2026. 5.2 LTS is supported to April 2028. 6.2 LTS is due in
  April 2027 and requires MySQL 8.4. From 2028, Django releases once a year with three years of
  support.
- Python 3.10 reached end of life in October 2026.
- Debian bookworm's regular security support has ended, and trixie is supported to 2030.
- DRF 3.18 dropped Django 4.2.
- Some installed dependencies are unused or duplicated.

## Options considered

- **Python 3.12 on bookworm:** shorter OS support.
- **Python 3.13 on trixie.**
- **Python 3.14 on trixie:** newer, so less ecosystem soak.

## Decision

1. **Lock dependencies with hashes** using uv. Remove unused and duplicate packages, including the
   Channels stack ([ADR-039](ADR-039-retire-channels-and-daphne.md)). Renovate keeps dependencies current.
2. **One Python jump,** decided by a one-day spike on `python:3.14-slim-trixie`. The spike checks
   gunicorn, the mysqlclient build, firebase-admin and grpcio, Pillow, reportlab and the full test
   tiers.
   - If it passes, move to 3.14.
   - If it fails, move to 3.13 and stay there through Django 6.2.
3. The base image is multi-stage and non-root, with build dependencies only in the builder stage.
4. **DRF 3.17** on the current Django, then **Django 5.2 LTS**. Django deprecation warnings are
   errors in new code first ([ADR-051](ADR-051-toolchain.md)).
5. **MySQL 8.4** ([ADR-002](ADR-002-mysql-8-4-lts.md)) comes before any Django release from 6.1 on.
6. **Django 6.2 LTS between Q4 2027 and Q1 2028,** well inside 5.2's support.
7. After that, upgrade to each yearly Django release within six months of its release.
8. **The authserver follows its own track** onto the same base image and LTS. Its identity DDL
   lands in `db-scripts` first ([ADR-021](ADR-021-separate-identity-schema.md)).

### Refinements (2026-11-21)

- DRF 3.17 runs on Django 4.2; DRF 3.18 follows Django 5.2, because 3.18 no longer supports 4.2.
- Until the Python jump, one Dockerfile with build arguments builds a `python:3.10-slim-bookworm` bridge image, because Django 4.2 can't run on Python 3.13. The jump itself stays a single step.
- Planned order: Django 5.2 in March 2027, before the exam window; the Python jump in April 2027; Django 6.2 LTS between Q4 2027 and Q1 2028.

## Consequences

- Supported versions throughout, with one predictable upgrade a year.

## Revisit when

- Each end-of-life date is six months away.

## Related ADRs

[ADR-002](ADR-002-mysql-8-4-lts.md), [ADR-039](ADR-039-retire-channels-and-daphne.md), [ADR-051](ADR-051-toolchain.md)
