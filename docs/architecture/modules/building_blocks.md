# `building_blocks`

**Status at `dev` 7fd66060:** not started. There is no `building_blocks/` package yet; the closest things today are `utils/response.py` (`CustomResponse`), `utils/permission.py` and the paginator in `utils/utils.py`.

## Purpose

Technical plumbing shared by every module: errors, ids, the API envelope and base views, authentication and authorization primitives, configuration, the outbound HTTP client, caching, messaging (outbox, relay, consumers, webhooks), health, flags, the business clock and test helpers. It holds **no business rules** ([ADR-017](../adr/ADR-017-one-layered-module-structure.md)).

## Kind

Plumbing. Not a business module: it has no `public.py`; modules import its packages directly.

## Tables it owns

| Table | Package | Notes |
|---|---|---|
| `outbox_event`, `inbox_record`, `dead_letter` | `messaging` | new, issue 0058 |
| `idempotency_record` | `api` | new, issue 0058 |
| `schedule_run` | `tasks` | new, issue 0066 |
| `feature_flag`, `feature_flag_change` | `flags` | new, issue 0073 |
| `service_client` | `auth` | new, issue 0089 |
| `audit_event` | `audit` | new; replaces `system_action_log` |

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `system_action_log` | `api/dashboard/company/company_views.py` :: `_notify_admins_company_action`<br>`api/dashboard/company/company_views.py` :: `post`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/events/manage_views.py` :: `post`<br>`api/dashboard/intern/leave/leave_views.py` :: `post`<br>`api/dashboard/intern/tasks/tasks_views.py` :: `patch`<br>`api/dashboard/intern/timesheet/timesheet_views.py` :: `patch`<br>`api/dashboard/manage_interns/interns_views.py` :: `patch`<br>`api/dashboard/manage_interns/leave/leave_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `post`<br>`api/dashboard/mentor/admin_views.py` :: `post`<br>`api/dashboard/mentor/mentor_views.py` :: `post`<br>`api/dashboard/mentor/opportunity_views.py` :: `post`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update` | — |

## Public API (public.py)

Each package exposes a small API, for example:

| Package | Main names |
|---|---|
| `errors` | `DomainError`, `error_code`, `NotFound`, `Conflict`, `Forbidden` |
| `ids` | `uuid7_str()` |
| `clock` | `now()`, `BUSINESS_TZ`, `period_bounds(kind, at)` |
| `api` | `MuLearnAPIView`, `PublicAPIView`, `InternalAPIView`, `idempotent`, `parse_query`, `parse_body`, `public_cache` |
| `authz` | `Principal`, `Grant`, `policy`, `require`, `principal_of` |
| `persistence` | `command` |
| `messaging` | `outbox.publish`, `IntegrationEvent`, `consumer`, `subscribe` |
| `http` | `get_client(name)` |
| `cache` | `get_or_compute` |
| `config` | `get(name)`, `config_check` |
| `flags` | `declare`, `is_on` |
| `health` | `live`, `ready`, `drain` |

## Events

None of its own. It carries every module's events.

## Allowed dependencies

Django, DRF, Celery and the standard library. It **never imports `modules` or the legacy packages** (`api`, `db`, `utils`, `mu_celery`). Only `building_blocks.http` imports an HTTP client.

## What moves from legacy code

- `utils/response.py` `CustomResponse` → `building_blocks.api` (the envelope keeps its shape)
- `utils/exception.py` → `building_blocks.errors`
- the paginator in `utils/utils.py` → `building_blocks.api` (keyset pagination next to the legacy paging)
- `system_action_log` writes → `building_blocks.audit` `audit_event`

## Cut-over steps

The foundation issues, in order:

1. [0009](../github-issues/0009-make-api-directories-packages.md): Make every directory under api/ a package (Phase 1)
1. [0010](../github-issues/0010-ruff-for-new-code.md): Add ruff with checks on new code (Phase 1)
1. [0014](../github-issues/0014-building-blocks-skeleton.md): Create the building_blocks package and its import contracts (Phase 1)
1. [0015](../github-issues/0015-uuid7-ids.md): Add UUIDv7 id helpers (Phase 1)
1. [0016](../github-issues/0016-business-clock.md): Add the business clock with IST period bounds (Phase 1)
1. [0017](../github-issues/0017-domain-error-registry.md): Add the DomainError registry with stable codes (Phase 1)
1. [0018](../github-issues/0018-request-context-and-json-logs.md): Add request ids and JSON logging (Phase 1)
1. [0019](../github-issues/0019-envelope-code-and-exception-handler.md): Add code and requestId to the envelope, with one exception handler (Phase 1)
1. [0020](../github-issues/0020-typed-configuration.md): Add typed configuration and config_check (Phase 1)
1. [0021](../github-issues/0021-command-decorator.md): Add the `@command` decorator and its transaction guard (Phase 1)
1. [0022](../github-issues/0022-outbound-http-client.md): Add the outbound HTTP client with timeouts and a circuit breaker (Phase 1)
1. [0023](../github-issues/0023-modules-package-and-generator.md): Add the modules package and the new_module generator (Phase 1)
1. [0026](../github-issues/0026-base-api-views.md): Add MuLearnAPIView and PublicAPIView (Phase 1)
1. [0027](../github-issues/0027-authz-core.md): Add principals, grants and the policy registry (Phase 1)
1. [0032](../github-issues/0032-health-endpoints.md): Add live and ready health endpoints with a drain flag (Phase 2)
1. [0043](../github-issues/0043-opentelemetry-and-sentry.md): Wire up OpenTelemetry and Sentry (Phase 2)
1. [0044](../github-issues/0044-slow-query-logging.md): Log slow queries with their request id (Phase 2)
1. [0058](../github-issues/0058-messaging-tables-alter.md): Create the outbox, inbox, dead-letter and idempotency tables (Phase 3)
1. [0059](../github-issues/0059-outbox-publish.md): Add the outbox models and outbox.publish_raw (Phase 3)
1. [0060](../github-issues/0060-cloudevents-envelope.md): Add IntegrationEvent with CloudEvents names and a payload test (Phase 3)
1. [0061](../github-issues/0061-outbox-relay.md): Add the outbox relay (Phase 3)
1. [0062](../github-issues/0062-consumers-inbox-and-dead-letters.md): Add consumers with inbox de-duplication, retries and dead letters (Phase 3)
1. [0063](../github-issues/0063-replay-and-purge-commands.md): Add dead-letter replay and outbox purge commands (Phase 3)
1. [0065](../github-issues/0065-task-base-class.md): Add a task base with time limits, acks_late and backoff (Phase 3)
1. [0066](../github-issues/0066-schedule-run-alter.md): Create the schedule_run table (Phase 3)
1. [0067](../github-issues/0067-schedule-slot-claims.md): Claim each scheduled slot once and record heartbeats (Phase 3)
1. [0069](../github-issues/0069-safe-enqueue.md): Add safe_enqueue for legacy .delay() calls (Phase 3)
1. [0073](../github-issues/0073-feature-flag-tables-alter.md): Create the feature flag tables (Phase 3)
1. [0074](../github-issues/0074-feature-flag-store.md): Add the persisted feature flag store (Phase 3)
1. [0089](../github-issues/0089-service-client-alter.md): Create the service_client table (Phase 4)
1. [0090](../github-issues/0090-service-clients.md): Add service clients and InternalAPIView (Phase 4)

## Tests this module needs

- Unit tests for every package, with no database where possible.
- The relay and consumers on the MySQL tier: two relays at once, redelivery, unknown versions, dead letters, replay.
- The `@command` guard raises when one module's command runs inside another's transaction.
- The payload test rejects personal-looking event keys.

## Open questions

- Which secret store each environment uses (SSM Parameter Store or Secrets Manager) is the platform admin's call.
