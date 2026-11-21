# Later: modules on demand and deferred items

| | |
|---|---|
| Epic | later-on-demand |
| Phase / milestone | Later: on demand |
| Labels | arch, phase:later, type:epic |

## What it will contain

**Modules that move when a feature needs them** ([ADR-038](../../adr/ADR-038-modules-own-their-tables.md)):
- `organizations` (with chapters, [ADR-028](../../adr/ADR-028-chapter-materialised-paths.md));
- `communities`, `learning`, `events`, `mentorship`, `careers`, `interns`, `media`, `projects`, `payments` and `administration`.

A legacy area moves into its module only when a change touches it, through the characterization-test recipe in [12-testing-and-quality-gates.md](../../12-testing-and-quality-gates.md).

**Deferred items, each waiting for its trigger** ([15-risks-and-future-scale.md](../../15-risks-and-future-scale.md)):
- Redis sorted-set boards;
- board definitions;
- packed-score leaderboard algorithms;
- read replicas and a database proxy;
- a search engine;
- hash-chained audit;
- asynchronous integrity detectors;
- RS256 tokens with JWKS;
- the `web-admin` and `web-public` pools;
- ECS;
- extracting a module into a service.

**Platform track:**
- the MySQL 8.4 upgrade, rehearsed on a restored snapshot and run outside the exam period;
- the Python upgrade on a supported base image;
- Django 6.2 LTS when it is released;
- the floating-point money-column migration.

## Entry conditions

The item's trigger has fired, or a feature needs the module.

## Exit criteria

Each item gets its own ADR update or detailed issues when it starts.
