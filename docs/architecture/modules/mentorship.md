# `mentorship`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Mentor applications, availability, sessions and interest-group opportunities.

## Kind

Supporting.

## Tables it owns

`mentor_application`, `mentor_availability_slot`, `mentor_karma_award`, `mentorship_session`, `mentorship_session_user_link`, `user_mentor`, `ig_opportunity`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `ig_opportunity` | `api/dashboard/mentor/opportunity_serializers.py` :: `create`<br>`api/dashboard/mentor/opportunity_serializers.py` :: `update`<br>`api/dashboard/mentor/opportunity_views.py` :: `delete`<br>`api/dashboard/mentor/opportunity_views.py` :: `post` | — |
| `mentor_application` | `api/dashboard/campus/campus_views.py` :: `post`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/mentor/mentor_views.py` :: `delete`<br>`api/dashboard/mentor/mentor_views.py` :: `patch`<br>`api/dashboard/mentor/mentor_views.py` :: `post`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/roles/dash_roles_views.py` :: `delete` | — |
| `mentor_availability_slot` | `api/dashboard/mentor/availability_views.py` :: `delete`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update` | — |
| `mentorship_session` | `api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/mentor/session_recurrence_helper.py` :: `generate_recurring_sessions`<br>`api/dashboard/mentor/session_views.py` :: `delete`<br>`api/dashboard/mentor/session_views.py` :: `patch`<br>`api/dashboard/mentor/session_views.py` :: `post`<br>`api/management/commands/transition_mentorship_session_statuses.py` :: `handle` | — |
| `mentorship_session_user_link` | `api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/mentor/session_views.py` :: `post`<br>`api/management/commands/transition_mentorship_session_statuses.py` :: `handle` | — |
| `user_mentor` | `api/dashboard/campus/campus_views.py` :: `post`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/mentor/admin_views.py` :: `post`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/register/serializers.py` :: `create` | — |

## Public API (public.py)

`mentors_for(ig_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `mentorship.mentor_approved`, `mentorship_session_completed` | none |

## Allowed dependencies

`communities.public`, `organizations.public`, `people.public`, `identity_access.public` (grant commands for the mentor scope).

## What moves from legacy code

`api/dashboard/mentor/`, `mu_celery/mentor_tasks.py`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Approving a mentor grants the mentor scope through `identity_access`, never by writing `user_role_link` directly.

## Open questions

None yet.
