# Risks and future scale

What could go wrong over the next five years, what in this architecture prevents it, how we would notice, and what to add when growth demands it. Security-specific risks are tracked privately by the maintainers and are not listed here.

## Failure modes

Each row is a way the backend could fail as it grows, written as a short story.

| # | Failure | Prevented by | Signal that it is starting |
|---|---|---|---|
| F-01 | A campus signup burst opens thousands of connections and MySQL refuses new ones | Workers × threads sized from the connection budget; per-service `MAX_USER_CONNECTIONS` ([ADR-006](adr/ADR-006-gunicorn-gthread-behind-nginx.md), [ADR-019](adr/ADR-019-read-scaling-and-connections.md)) | Connections above 80% of budget; error 1040 |
| F-02 | A slow dependency (the authserver, SMTP, Discord) holds every thread, and the API hangs | Timeouts, circuit breakers, no network inside transactions, the in-app deadline | p99 latency climbs while CPU is idle; breaker-open events |
| F-03 | The same award is applied twice after a retry or a replayed reaction | Ledger keys `UNIQUE(source, source_ref)`, the submission state machine, row locks ([ADR-004](adr/ADR-004-karma-ledger.md)) | Reconciliation drift; duplicate-key conflicts in logs |
| F-04 | Awards are lost while the Discord bot is down, and nobody notices for days | Bot heartbeat on processed events; the desired-state reconciler ([ADR-018](adr/ADR-018-channel-agnostic-contributions.md)) | Heartbeat alert within 10 minutes of channel activity with no processing |
| F-05 | A follow-up (level-up, notification) is lost because the broker was down at commit | The transactional outbox and `safe_enqueue` ([ADR-005](adr/ADR-005-transactional-outbox.md)) | Outbox lag above 5 minutes |
| F-06 | A consumer bug silently drops events after a schema change | Version-tolerant routing; unknown versions go to dead letters with an alert | Dead-letter count above 0 |
| F-07 | Two beats run after a failover, and every scheduled job runs twice | `schedule_run` slot claims ([ADR-042](adr/ADR-042-background-work-celery.md)) | Duplicate-claim conflicts; heartbeats from two hosts |
| F-08 | Code ships before the schema it needs and crash-loops every container | Required schema ids checked at pre-flight and boot ([ADR-040](adr/ADR-040-db-scripts-safety-net.md)) | Deploy pre-flight refusal (the failure is caught before users see it) |
| F-09 | Models and the real schema drift apart until a release breaks | Parity tests in CI; the nightly drift report | Drift report entries; parity failures |
| F-10 | A contributor's test run wipes a shared database | The test guard (issue 0001); `test_` database names only | The guard refusing to start |
| F-11 | A role combination grants more than any single role should | The union-of-grants rule and its property test ([ADR-007](adr/ADR-007-scoped-grants-and-policies.md)) | Property-test failure in CI |
| F-12 | Authorization erodes as new views forget permission checks | Default deny and the auth-coverage ratchet | Ratchet failure in CI |
| F-13 | Module boundaries erode until the codebase is a tangle again | Import contracts, fitness functions and shrink-only allowlists ([ADR-016](adr/ADR-016-architecture-enforced-by-automation.md)) | Allowlists stop shrinking for two releases |
| F-14 | Leaderboards slow to seconds as karma rows grow | Period totals as a read model; cached public boards ([ADR-024](adr/ADR-024-leaderboards-and-period-totals.md)) | Board p95 above 150 ms |
| F-15 | Monthly boards put awards in the wrong month around midnight IST | `period_bounds` in IST everywhere ([ADR-053](adr/ADR-053-business-calendar-and-money.md)) | Month-boundary tests in CI |
| F-16 | Cache eviction drops rate-limit or lock state, so limits silently stop working | Separate non-evicting `redis-state` ([ADR-043](adr/ADR-043-redis-cache-and-state.md)) | `evicted_keys` above 0 on `redis-state` |
| F-17 | A bulk export or import starves urgent work | Separate queues and worker groups; exports as jobs | `critical` queue age above 30 s |
| F-18 | Old app builds break after an API change | Additive-only `/api/v1`; the OpenAPI diff gate; `X-App-Version` ([ADR-044](adr/ADR-044-api-standards-v1-2.md)) | Error rate by app version |
| F-19 | A privacy obligation (consent, minors, erasure) is missed by the legal date | Phase 7 with counsel; erasure that anonymises without deleting history ([ADR-052](adr/ADR-052-privacy-minors-erasure.md)) | The phase gate not met by its date |
| F-20 | A bad release can't be rolled back quickly | Images by digest; `deploy.sh` rollback rehearsed before each cut-over ([ADR-013](adr/ADR-013-immutable-images-by-digest.md)) | Rollback drill time over 5 minutes |
| F-21 | Logs or events leak personal data to processors | Payload tests; no personal fields in logs or traces ([ADR-012](adr/ADR-012-opentelemetry-sentry-json-logs.md)) | Redaction-filter hits; payload-test failures |
| F-22 | The μCoin integration starts writing back into core | One-way webhooks; `mucoin-service` holds no token signing key ([ADR-054](adr/ADR-054-mucoin-external-consumer.md)) | Any inbound call from `mucoin-service` to a write endpoint |

## Risk register

| # | Risk | Owner | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| R-01 | The gunicorn cut-over regresses under real traffic (thread safety, a missed signal receiver) | Backend maintainer + platform admin | Medium | High | A staging soak, the slow-dependency load test, a rollback rehearsal; persistent connections stay off for one clean week |
| R-02 | The ledger backfill loads the primary at a bad time | Backend maintainer | Medium | Medium | Batches of 5,000, off-peak, resumable, aborted on high CPU or lock waits; dry run first |
| R-03 | Shadow-mode diffs for the bot reveal rule differences nobody can explain | Backend maintainer + bot maintainer | Medium | High | No switch until every difference is explained; per-command flags |
| R-04 | Contributors pick up issues out of order or stall on large ones | Maintainers | High | Medium | Explicit dependencies, `status:blocked`, sizes capped at about two days, claiming by comment |
| R-05 | Review capacity is too thin for `core-review` issues | Maintainers | High | Medium | `core-review` kept narrow; review rota; the issues on the critical path are flagged in the roadmap |
| R-06 | Parity tests surface more schema drift than expected | Platform admin | High | Medium | Known drift goes into a shrink-only allowlist with an owner per entry; fix incrementally |
| R-07 | The Django 5.2 upgrade breaks behaviour that tests don't cover | Backend maintainer | Medium | High | Characterization tests on the busiest routes; a two-week staging soak; one high-risk change per train |
| R-08 | The privacy legal date arrives before Phase 7 | Maintainers + counsel | Medium | High | Start the Phase 7 design early; signup accepts the new fields before clients send them |
| R-09 | The vendored schema falls behind `db-scripts` | Platform admin | Medium | Medium | A refresh pull request after every alter merge, on the maintainers' merge checklist; the nightly drift report shows any gap |
| R-10 | Infrastructure cost grows faster than the budget | Platform admin | Low | Medium | Cost budget alarms; every new component waits for its trigger |
| R-11 | The private security work slips, holding the cut-over | Maintainers | Medium | High | The roadmap gates the cut-over on it explicitly; the rest of the plan continues |
| R-12 | `mucoin-service` needs a token scheme change before it can accept tickets (on hold with the μCoin integration) | μCoin maintainer | Medium | Low | Tickets are a small, documented HMAC; JWKS replaces them in key-separation phase 2 |

## Scale tiers and their triggers

The backend grows by adding the next component only when its trigger fires. Until then the simpler setup stays.

| Tier | Setup | Moves to the next tier when |
|---|---|---|
| 1 | Two app nodes (today's main node and pod 1), one of them running beat; RDS Multi-AZ; two Redis roles; one worker group per queue family | A second node is needed for availability or load (Phase 2 plans it anyway) |
| 2 | Two or more app nodes behind the load balancer in two zones; routed worker groups; persistent connections | Primary CPU p95 above 60% at peak for two weeks, or report and admin load above 20% of the primary → **read replica**. More than 8 app nodes, or a connection budget above 60% of `max_connections` with high churn → **RDS Proxy** ([ADR-019](adr/ADR-019-read-scaling-and-connections.md)) |
| 3 | A replica for `@replica_safe` selectors; separate `web-admin` and `web-public` pools | Four or more app nodes, autoscaling for national events, or more than a day a month of host operations → **ECS on Fargate** ([ADR-049](adr/ADR-049-deployment-platform-and-dr.md)) |
| 4 | ECS services per role | Five or more independently deployed services owned by separate teams → Kubernetes. Not planned. |

**Component triggers:**

| Component | Trigger | ADR |
|---|---|---|
| Redis sorted-set boards | Board p95 above 150 ms with indexed totals, awards above 50/s sustained, or a board above 500,000 members | [024](adr/ADR-024-leaderboards-and-period-totals.md) |
| Configurable board definitions | A second state is onboarded, or the national board launches | [029](adr/ADR-029-board-definitions.md) |
| Packed-score leaderboard algorithms | Any board passes 1 million members | [030](adr/ADR-030-leaderboard-algorithms.md) |
| A search engine | Search p95 above 300 ms, or search above 5% of primary load (MySQL FULLTEXT first) | [020](adr/ADR-020-search-on-trigger.md) |
| Ledger partitioning by month | Awards above about 100/s sustained | [004](adr/ADR-004-karma-ledger.md) |
| A different event transport | Events above about 5,000/s, or a replay window beyond 7 days | [005](adr/ADR-005-transactional-outbox.md) |
| Hash-chained audit | Notified as a Significant Data Fiduciary, counsel advises it, or a dispute needs provable history | [032](adr/ADR-032-audit-trail-and-retention.md) |
| Asynchronous abuse detectors | The national board launches, or reported abuse above 1% of awards in a month | [034](adr/ADR-034-contribution-integrity.md) |
| Extracting a module into a service | All five conditions in [ADR-001](adr/ADR-001-domain-oriented-modular-monolith.md) hold | [001](adr/ADR-001-domain-oriented-modular-monolith.md) |
| PostgreSQL | All external writers behind the API, a measured need that blocks releases, and an estimate under one quarter of team time | [002](adr/ADR-002-mysql-8-4-lts.md) |

## Capacity claims

No number of users is claimed until the capacity model in [09-performance-and-caching.md](09-performance-and-caching.md) has measured inputs and the load tests have passed. The capacity statement is published with the load-test results, and re-checked at every tier change.
