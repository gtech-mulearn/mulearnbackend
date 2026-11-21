# Set up dashboards, SLO alerts and paging

| | |
|---|---|
| ID | 0048 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M, maintainer-only |
| Depends on | 0043 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

Telemetry is only useful if someone is told when things go wrong. The first SLOs, and the bot heartbeat when it exists, need dashboards and paging ([ADR-033](../adr/ADR-033-slos-and-burn-rate-alerts.md), [11-reliability-and-observability.md](../11-reliability-and-observability.md#slos-and-alerts)).

## Before you start

- Maintainer-only: it needs access to the observability accounts.
- Issue 0043 must be merged.

## What to do

1. Set up the collector and Grafana Cloud data sources for each environment.
2. Build dashboards:
   - request rate, errors and latency per route family;
   - database connections against the budget;
   - queue depth and age.
3. Create alerts for API availability (fast and slow burn), `critical` queue age and error-rate spikes.
4. Set paging for 07:00–23:00 IST, with the ops channel out of hours.
5. Write a runbook for each page, in `docs/runbooks/`.

## Acceptance criteria

- [ ] Each alert fires in a drill, and its runbook link works.
- [ ] No dashboard shows a personal identifier.

## How to test

Run one drill per alert on staging, and record the results on the issue.

## Out of scope

- Outbox, schedule and bot alerts. They are added by the issues that create those signals.

## Notes for reviewers

No page may go live without its runbook.
