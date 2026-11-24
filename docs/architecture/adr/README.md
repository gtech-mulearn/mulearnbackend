# Architecture decision records

Each record states the context, the options considered, the decision, its consequences, and when to
revisit it. Each one also says where the decision stands in the code at `dev` 7fd66060 (21 Nov 2026).
The set was first accepted on 17 Nov 2026 and last revised on 21 Nov 2026.

## Index

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](ADR-001-domain-oriented-modular-monolith.md) | Domain-oriented modular monolith | Accepted |
| [ADR-002](ADR-002-mysql-8-4-lts.md) | Stay on MySQL; upgrade to 8.4 LTS | Accepted |
| [ADR-003](ADR-003-one-owner-per-table.md) | One owner per table; external writers become API clients | Accepted |
| [ADR-004](ADR-004-karma-ledger.md) | Karma is an append-only ledger; the wallet is a projection | Accepted (amended 2026-11-21) |
| [ADR-005](ADR-005-transactional-outbox.md) | Transactional outbox relayed to Celery on Redis | Accepted (amended 2026-11-21) |
| [ADR-006](ADR-006-gunicorn-gthread-behind-nginx.md) | gunicorn `gthread` behind nginx and a load balancer | Accepted (amended 2026-11-21) |
| [ADR-007](ADR-007-scoped-grants-and-policies.md) | Scoped grants and resource-aware policies | Accepted (amended 2026-11-21) |
| [ADR-008](ADR-008-authserver-separate-idp.md) | The authserver remains a separate identity provider | Accepted |
| [ADR-009](ADR-009-selective-cqrs-projections.md) | Selective CQRS with same-database projections | Accepted (amended 2026-11-21) |
| [ADR-010](ADR-010-api-contract-envelope.md) | API contract 1.1 (additive) on `/api/v1` | Accepted |
| [ADR-011](ADR-011-object-storage-stateless-nodes.md) | Object storage for files; stateless nodes | Accepted (amended 2026-11-21) |
| [ADR-012](ADR-012-opentelemetry-sentry-json-logs.md) | OpenTelemetry, Sentry and JSON logs | Accepted (amended 2026-11-21) |
| [ADR-013](ADR-013-immutable-images-by-digest.md) | Immutable images, promoted by digest | Accepted |
| [ADR-014](ADR-014-db-scripts-single-schema-source.md) | `db-scripts` is the permanent, single source of schema | Accepted |
| [ADR-015](ADR-015-uuid-keys-and-public-ids.md) | Keep UUID `VARCHAR(36)` keys; BIGINT for new append-heavy tables; UUIDv7 for new ids | Accepted (amended 2026-11-21) |
| [ADR-016](ADR-016-architecture-enforced-by-automation.md) | Architecture enforced by automation | Accepted (amended 2026-11-21) |
| [ADR-017](ADR-017-one-layered-module-structure.md) | One layered structure for every module, with shared plumbing in `building_blocks` | Accepted |
| [ADR-018](ADR-018-channel-agnostic-contributions.md) | A channel-agnostic contributions API with reconciliation | Accepted (amended 2026-11-21) |
| [ADR-019](ADR-019-read-scaling-and-connections.md) | Read scaling: persistent connections, budgets, a proxy and replicas on triggers | Accepted (amended 2026-11-21) |
| [ADR-020](ADR-020-search-on-trigger.md) | MySQL FULLTEXT first; a search engine on trigger | Accepted |
| [ADR-021](ADR-021-separate-identity-schema.md) | A separate identity schema and database user | Accepted (amended 2026-11-21) |
| [ADR-022](ADR-022-no-cross-module-transactions.md) | Transactions never cross module boundaries | Accepted (amended 2026-11-21) |
| [ADR-023](ADR-023-one-image-several-roles.md) | One image, several deployment roles (phased) | Accepted (amended 2026-11-21) |
| [ADR-024](ADR-024-leaderboards-and-period-totals.md) | Leaderboards from durable period totals; sorted sets on trigger | Accepted (amended 2026-11-21) |
| [ADR-025](ADR-025-serving-model-evolution.md) | Serving-model evolution | Superseded by ADR-006 |
| [ADR-026](ADR-026-performance-budgets-in-ci.md) | Performance budgets are CI gates | Accepted |
| [ADR-027](ADR-027-split-content-module.md) | Split the `content` grab-bag into cohesive modules | Accepted |
| [ADR-028](ADR-028-chapter-materialised-paths.md) | A chapter hierarchy with materialised paths | Accepted |
| [ADR-029](ADR-029-board-definitions.md) | Leaderboards as configurable board definitions | Deferred (a second state is onboarded, or the national board launches) |
| [ADR-030](ADR-030-leaderboard-algorithms.md) | Leaderboard algorithms: packed scores, exact top-K, approximate long-tail ranks | Deferred (any board passes 1 million members) |
| [ADR-031](ADR-031-feature-flags.md) | Feature flags: the persisted flag store is the single mechanism | Replaced 2026-11-21 |
| [ADR-032](ADR-032-audit-trail-and-retention.md) | Audit trail and retention | Accepted (amended 2026-11-21) |
| [ADR-033](ADR-033-slos-and-burn-rate-alerts.md) | SLOs and burn-rate alerting for a volunteer team | Accepted (amended 2026-11-21) |
| [ADR-034](ADR-034-contribution-integrity.md) | Contribution integrity | Accepted in part |
| [ADR-035](ADR-035-cloudevents-envelope.md) | CloudEvents 1.0 attribute names for integration events | Accepted (amended 2026-11-21) |
| [ADR-036](ADR-036-rate-limiting.md) | Rate limiting and abuse controls | Accepted (amended 2026-11-21) |
| [ADR-037](ADR-037-weekly-release-train.md) | Weekly release train with flag-driven releases | Accepted |
| [ADR-038](ADR-038-modules-own-their-tables.md) | Modules are Django apps that own their tables | Accepted (new 2026-11-21) |
| [ADR-039](ADR-039-retire-channels-and-daphne.md) | Retire Channels and Daphne; realtime through push and conditional polling | Accepted (new 2026-11-21) |
| [ADR-040](ADR-040-db-scripts-safety-net.md) | A safety net for `db-scripts` schema ownership | Accepted (new 2026-11-21) |
| [ADR-041](ADR-041-transactions-and-consistency.md) | Transaction and consistency rules | Accepted (new 2026-11-21) |
| [ADR-042](ADR-042-background-work-celery.md) | Background work: Celery with routed queues and exactly-once schedule slots | Accepted (new 2026-11-21) |
| [ADR-043](ADR-043-redis-cache-and-state.md) | Redis: an evictable cache and a non-evicting state store | Accepted (new 2026-11-21) |
| [ADR-044](ADR-044-api-standards-v1-2.md) | API standards v1.2 on DRF | Accepted (new 2026-11-21) |
| [ADR-045](ADR-045-hot-path-serialization.md) | Serialization on hot paths | Accepted (new 2026-11-21) |
| [ADR-046](ADR-046-tokens-keys-service-clients.md) | Tokens, keys and service clients | Accepted (new 2026-11-21) |
| [ADR-047](ADR-047-notification-pipeline.md) | One notification pipeline | Accepted (new 2026-11-21) |
| [ADR-048](ADR-048-typed-configuration.md) | Typed, fail-fast configuration and secrets | Accepted (new 2026-11-21) |
| [ADR-049](ADR-049-deployment-platform-and-dr.md) | Deployment platform, region and disaster recovery | Accepted (new 2026-11-21) |
| [ADR-050](ADR-050-platform-versions.md) | Platform versions and upgrade cadence | Accepted (new 2026-11-21) |
| [ADR-051](ADR-051-toolchain.md) | Toolchain | Accepted (new 2026-11-21) |
| [ADR-052](ADR-052-privacy-minors-erasure.md) | Privacy, minors and erasure (DPDP) | Accepted (new 2026-11-21) |
| [ADR-053](ADR-053-business-calendar-and-money.md) | Business calendar and money types | Accepted (new 2026-11-21) |
| [ADR-054](ADR-054-mucoin-external-consumer.md) | μCoin is an external consumer of integration events | Accepted, on hold (2026-11-21) |

## How the ADR process works

1. **When you need an ADR.** Write one when a change:
   - alters a rule in [the module rules](../04-module-rules.md);
   - adds a runtime dependency, a datastore or a deployment role;
   - changes a public API contract or an event contract;
   - changes a module boundary or table ownership;
   - changes how authentication, authorization, the karma ledger or payments work.
2. **How to propose one.**
   - Copy an existing record and take the next free number.
   - Set the status to `Proposed` and open a pull request that contains only the record (or the
     record and a small spike).
   - Link it from the pull request that will implement it.
3. **Who decides.**
   - The module owner (from `CODEOWNERS`) and one architecture maintainer must approve.
   - Records touching authentication, authorization, the ledger or payments need two maintainer
     approvals.
4. **Never edit an accepted decision; supersede it.**
   - Write a new record that states what it replaces.
   - Set the old record's status to `Superseded by ADR-0xx` (or `Amended`).
   - Leave the old text in place, so the history stays readable.
5. **Deferred records** name their trigger. When the trigger fires, the record is reopened as a
   proposal.
6. **Keep checks in step.** If a decision is enforced by a CI check (import-linter, a fitness test,
   a ratchet), change the check in the same pull request as the record.

### Statuses

| Status | Meaning |
|---|---|
| Proposed | Under review. |
| Accepted | In force. |
| Accepted (amended) | In force. A later review changed part of the original decision, and the record shows the current text. |
| Replaced | The original decision was withdrawn, and the record states its replacement. |
| Superseded by ADR-0xx | No longer in force. Read the named record. |
| Deferred | Not in force until its named trigger fires. |
