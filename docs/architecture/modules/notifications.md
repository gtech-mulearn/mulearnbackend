# `notifications`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The in-app inbox, broadcasts, push and email delivery, preferences, quiet hours and templates. Other modules never send anything themselves: they publish domain events, and `notifications` maps them to templates ([ADR-047](../adr/ADR-047-notification-pipeline.md)).

## Kind

Generic.

## Tables it owns

`notification`, `broadcast_notification`, `broadcast_notification_read`, the push device, preference and delivery tables, and the team-notification tables (in flight in #3289). `notification_log` is taken over when the grit meter is absorbed.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `broadcast_notification` | `api/dashboard/events/manage_views.py` :: `delete`<br>`api/notification/broadcast_utils.py` :: `create_broadcast`<br>`api/notification/notification_view.py` :: `delete`<br>`api/notification/notification_view.py` :: `post` | — |
| `broadcast_notification_read` | `api/notification/notification_view.py` :: `_archive_broadcast_for_user`<br>`api/notification/notification_view.py` :: `_sync_broadcast_receipts`<br>`api/notification/notification_view.py` :: `patch` | — |
| `notification` | `api/dashboard/events/manage_views.py` :: `delete`<br>`api/notification/notification_view.py` :: `delete`<br>`api/notification/notification_view.py` :: `patch`<br>`api/notification/notifications_utils.py` :: `insert_notification`<br>`api/notification/service.py` :: `_write_notifications` | — |
| `notification_log` | none | scheduler-service |
| `push_campaign` | `api/push/views.py` :: `post`<br>`mu_celery/push_tasks.py` :: `send_campaign_chunk`<br>`mu_celery/push_tasks.py` :: `start_campaign` | — |
| `push_config` | `api/push/config.py` :: `set_config` | — |
| `push_delivery_log` | `api/push/sender.py` :: `deliver`<br>`api/push/views.py` :: `post`<br>`mu_celery/push_tasks.py` :: `purge_push_logs` | — |
| `user_push_device` | `api/push/sender.py` :: `deliver`<br>`api/push/views.py` :: `delete`<br>`api/push/views.py` :: `post` | — |
| `user_push_preference` | `api/push/views.py` :: `patch` | — |

## Public API (public.py)

`unread_count(user_id)`, `inbox(user_id, cursor)`. `notify(user_ids, template, data, dedupe_key)` is internal to this module.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| none (delivery metrics only) | the domain events it maps to templates, for example `contributions.submission_approved`, `gamification.level_changed`, `events.event_cancelled` |

## Allowed dependencies

`people.public`, `identity_access.public`, plus any module whose batch selectors it needs, declared in `module_graph.toml`.

## What moves from legacy code

- `api/notification/`, `api/push/`, `mu_celery/push_tasks.py`
- the email sends on request paths

## Cut-over steps

1. [Epic: Phase 6: gamification and notifications](../github-issues/epics/phase-6-gamification-and-notifications.md)

## Tests this module needs

- The same envelope delivered twice produces one notification per user.
- Quiet hours defer delivery as due rows, never as long Celery ETAs.
- No SMTP call runs on a request path.

## Open questions

- Coordinate the team-notification work in #3289 before this module starts.
