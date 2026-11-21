# `events`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Events, interests and collaborators, the calendar, hackathons and event categories.

## Kind

Supporting.

## Tables it owns

`events`, `events_connection`, `events_interest`, `events_log`, `event_tag`, `event_tag_link`, `hackathon`, `hackathon_form`, `hackathon_organiser_link`, `hackathon_submission`, `categories`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `categories` | `api/dashboard/category/category_serializer.py` :: `create`<br>`api/dashboard/category/category_serializer.py` :: `update`<br>`api/dashboard/category/category_views.py` :: `delete`<br>`api/dashboard/category/category_views.py` :: `patch`<br>`api/dashboard/category/category_views.py` :: `post`<br>`api/dashboard/category/category_views.py` :: `put` | — |
| `events` | `api/dashboard/events/manage_views.py` :: `_update`<br>`api/dashboard/events/manage_views.py` :: `post`<br>`api/dashboard/events/public_views.py` :: `delete`<br>`api/dashboard/events/public_views.py` :: `post`<br>`api/dashboard/events/serializers.py` :: `create`<br>`api/dashboard/events/serializers.py` :: `update`<br>`api/management/commands/transition_event_statuses.py` :: `handle` | — |
| `events_connection` | `api/dashboard/company/collaboration_views.py` :: `_auto_wire_event_connection`<br>`api/dashboard/events/manage_views.py` :: `delete`<br>`api/dashboard/events/manage_views.py` :: `post` | — |
| `events_interest` | `api/dashboard/events/public_views.py` :: `delete`<br>`api/dashboard/events/public_views.py` :: `post` | — |
| `events_log` | `api/dashboard/events/event_logger.py` :: `log_event_action` | — |
| `hackathon` | `api/hackathon/hackathon_views.py` :: `post`<br>`api/hackathon/hackathon_views.py` :: `put`<br>`api/hackathon/serializer.py` :: `create`<br>`api/hackathon/serializer.py` :: `update` | — |
| `hackathon_form` | `api/hackathon/serializer.py` :: `create`<br>`api/hackathon/serializer.py` :: `update` | — |
| `hackathon_organiser_link` | `api/hackathon/hackathon_views.py` :: `post`<br>`api/hackathon/serializer.py` :: `create` | — |
| `hackathon_submission` | `api/hackathon/hackathon_views.py` :: `post`<br>`api/hackathon/serializer.py` :: `create` | — |

## Public API (public.py)

`event(event_id)`, `upcoming(scope)`, `bookmarker_ids(event_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `events.event_published`, `event_status_changed`, `event_cancelled`, `event_interest_registered` | none |

## Allowed dependencies

`learning.public`, `communities.public`, `organizations.public`, `identity_access.public`.

## What moves from legacy code

`api/dashboard/events/`, `api/hackathon/`, `api/calendar/`, `mu_celery/event_cron.py`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Status transitions run once per slot, through schedule claims.

## Open questions

None yet.
