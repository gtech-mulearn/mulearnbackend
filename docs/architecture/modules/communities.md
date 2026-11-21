# `communities`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Interest groups, their campus chapters, channels, learning circles and interest-group membership.

## Kind

Supporting.

## Tables it owns

`interest_group`, `user_ig_link`, `campus_ig_chapter`, `channel`, `learning_circle` (with its cached columns), `user_circle_link`, `circle_meeting_log`, `circle_meet_attendees`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `campus_ig_chapter` | `api/dashboard/campus/campus_views.py` :: `delete`<br>`api/dashboard/campus/events_views.py` :: `delete`<br>`api/dashboard/campus/events_views.py` :: `post`<br>`api/dashboard/campus/serializers.py` :: `create`<br>`api/dashboard/campus/serializers.py` :: `update` | — |
| `channel` | `api/dashboard/channels/channel_views.py` :: `delete`<br>`api/dashboard/channels/channel_views.py` :: `post`<br>`api/dashboard/channels/channel_views.py` :: `put`<br>`api/dashboard/channels/serializers.py` :: `create`<br>`api/dashboard/channels/serializers.py` :: `update` | Discord bot |
| `circle_meet_attendees` | `api/dashboard/learningcircle/learningcircle_serializer.py` :: `create`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `delete`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `post` | — |
| `circle_meeting_log` | `api/dashboard/lc/dash_lc_serializer.py` :: `create`<br>`api/dashboard/lc/dash_lc_view.py` :: `post`<br>`api/dashboard/learningcircle/learningcircle_serializer.py` :: `create`<br>`api/dashboard/learningcircle/learningcircle_serializer.py` :: `update`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `post`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `put` | — |
| `interest_group` | `api/dashboard/company/company_views.py` :: `_deactivate_company`<br>`api/dashboard/company/ig_sponsorship_views.py` :: `patch`<br>`api/dashboard/company/ig_sponsorship_views.py` :: `post`<br>`api/dashboard/ig/dash_ig_view.py` :: `delete`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/ig/dash_ig_view.py` :: `post`<br>`api/dashboard/ig/dash_ig_view.py` :: `put` | — |
| `learning_circle` | `api/dashboard/lc/dash_lc_serializer.py` :: `create`<br>`api/dashboard/lc/dash_lc_serializer.py` :: `update`<br>`api/dashboard/lc/dash_lc_view.py` :: `post`<br>`api/dashboard/lc/dash_lc_view.py` :: `put`<br>`api/dashboard/learningcircle/learningcircle_serializer.py` :: `create`<br>`api/dashboard/learningcircle/learningcircle_serializer.py` :: `update`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `delete`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `post`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `put`<br>`mu_celery/learning_circle_aggregates_cron.py` :: `_refresh_learning_circle_aggregates` | — |
| `user_circle_link` | `api/dashboard/lc/dash_lc_serializer.py` :: `create`<br>`api/dashboard/lc/dash_lc_serializer.py` :: `update`<br>`api/dashboard/lc/dash_lc_view.py` :: `delete`<br>`api/dashboard/lc/dash_lc_view.py` :: `patch`<br>`api/dashboard/lc/dash_lc_view.py` :: `post`<br>`api/dashboard/learningcircle/learningcircle_serializer.py` :: `create`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `delete`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `patch`<br>`api/dashboard/learningcircle/learningcircle_views.py` :: `post` | — |
| `user_ig_link` | `api/dashboard/campus/ig_views.py` :: `delete`<br>`api/dashboard/campus/ig_views.py` :: `post`<br>`api/dashboard/ig/dash_ig_view.py` :: `delete`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/ig/dash_ig_view.py` :: `post`<br>`api/dashboard/mentor/dash_mentor_helper.py` :: `reconcile_mentor_ig_links`<br>`api/dashboard/mentor/dash_mentor_helper.py` :: `release_mentor_ig_links`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/profile/profile_serializer.py` :: `update`<br>`api/dashboard/user/dash_user_serializer.py` :: `update`<br>`api/register/serializers.py` :: `create` | Discord bot |

## Public API (public.py)

`igs_of(user_ids)`, `circle(circle_id)`, `members_of(ig_id, cursor)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `communities.ig_membership_changed`, `learning_circle_meeting_reported` | `contributions.karma_awarded` (learning-circle aggregates) |

## Allowed dependencies

`organizations.public`, `people.public`, `identity_access.public`.

## What moves from legacy code

- `api/dashboard/ig/`, `api/dashboard/lc/`, `api/dashboard/learningcircle/`, `api/dashboard/channels/`
- `mu_celery/learning_circle_aggregates_cron.py`
- the learning-circle karma writes move to `contributions` in issue 0096

## Cut-over steps

1. [0007](../github-issues/0007-add-interest-group-image-columns.md): Add the interest-group image key columns to db-scripts (Phase 0)
1. [0096](../github-issues/0096-move-learning-circle-karma-writes.md): Move learning-circle karma writes onto contributions (Phase 4)
1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- A reported meeting produces one award per attendee, even when the event is redelivered.

## Open questions

- The interest-group image upload contract, being settled with #3145 in flight.
