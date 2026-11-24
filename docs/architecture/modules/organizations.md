# `organizations`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The organisation registry, colleges, departments, geography, chapters, memberships, organisation karma types and organisation aggregates.

## Kind

Supporting.

## Tables it owns

- `organization` (with its cached aggregate columns), `college`, `department`, `country`, `state`, `zone`, `district`
- `org_affiliation`, `org_discord_link`, `org_karma_log`, `org_karma_type`, `unverified_organization`, `user_organization_link`
- `community_partner`, `ig_community_partner_link`, `campus_execom_role`, `campus_social_link`, `college_showcase`, `enabler_campus_note`
- new: `org_chapter` (the federated chapter hierarchy; [ADR-028](../adr/ADR-028-chapter-materialised-paths.md)), `user_chapter_history`

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `campus_execom_role` | `api/dashboard/campus/dash_campus_helper.py` :: `ensure_ig_execom_catalog_entries`<br>`api/dashboard/campus/events_views.py` :: `post`<br>`api/dashboard/ig/dash_ig_view.py` :: `put` | — |
| `campus_social_link` | `api/dashboard/campus/campus_views.py` :: `delete`<br>`api/dashboard/campus/serializers.py` :: `create` | — |
| `college` | `api/dashboard/organisation/serializers.py` :: `create`<br>`api/dashboard/organisation/serializers.py` :: `update` | Discord bot |
| `college_showcase` | `api/dashboard/campus/serializers.py` :: `create`<br>`api/dashboard/campus/serializers.py` :: `update` | — |
| `community_partner` | `api/dashboard/community_partner/views.py` :: `post` | — |
| `country` | `api/dashboard/location/location_views.py` :: `delete` | — |
| `department` | `api/dashboard/organisation/organisation_views.py` :: `delete`<br>`api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/organisation_views.py` :: `put`<br>`api/dashboard/organisation/serializers.py` :: `create`<br>`api/dashboard/organisation/serializers.py` :: `update` | — |
| `district` | `api/dashboard/location/location_views.py` :: `delete` | — |
| `enabler_campus_note` | `api/dashboard/enabler/enabler_views.py` :: `delete`<br>`api/dashboard/enabler/serializers.py` :: `create`<br>`api/dashboard/enabler/serializers.py` :: `update` | — |
| `ig_community_partner_link` | `api/dashboard/community_partner/views.py` :: `_sync_ig_links` | — |
| `org_affiliation` | `api/dashboard/affiliation/affiliation_views.py` :: `delete`<br>`api/dashboard/affiliation/affiliation_views.py` :: `post`<br>`api/dashboard/affiliation/affiliation_views.py` :: `put`<br>`api/dashboard/affiliation/serializers.py` :: `create`<br>`api/dashboard/affiliation/serializers.py` :: `update`<br>`api/dashboard/organisation/organisation_views.py` :: `delete`<br>`api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/organisation_views.py` :: `put`<br>`api/dashboard/organisation/serializers.py` :: `create`<br>`api/dashboard/organisation/serializers.py` :: `update` | — |
| `org_karma_log` | `api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/serializers.py` :: `create` | — |
| `org_karma_type` | `api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/serializers.py` :: `create` | — |
| `organization` | `api/dashboard/company/serializers.py` :: `update`<br>`api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/organisation_views.py` :: `put`<br>`api/dashboard/organisation/serializers.py` :: `create`<br>`api/dashboard/organisation/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`mu_celery/org_aggregates_cron.py` :: `_refresh_org_aggregates` | Discord bot |
| `state` | `api/dashboard/location/location_views.py` :: `delete` | — |
| `unverified_organization` | `api/dashboard/organisation/serializers.py` :: `update`<br>`api/register/serializers.py` :: `create` | — |
| `user_organization_link` | `api/dashboard/campus/serializers.py` :: `update`<br>`api/dashboard/college/college_view.py` :: `patch`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/company/serializers.py` :: `update`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/organisation/organisation_views.py` :: `post`<br>`api/dashboard/organisation/serializers.py` :: `update`<br>`api/dashboard/profile/profile_serializer.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/user/dash_user_serializer.py` :: `create`<br>`api/dashboard/user/dash_user_serializer.py` :: `update`<br>`api/dashboard/user/dash_user_views.py` :: `patch`<br>`api/register/serializers.py` :: `create`<br>`mu_celery/alumni_cron.py` :: `update_alumni_status_cron` | — |
| `zone` | `api/dashboard/location/location_views.py` :: `delete` | — |

## Public API (public.py)

`chapter_path_of(org_id)`, `ancestors(path)`, `memberships_of(user_ids)`, `organization(org_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `organizations.organization_membership_changed`, `organization_created`, `chapter_created` | `contributions.karma_awarded` (batched into the cached columns) |

## Allowed dependencies

`people.public`, `identity_access.public`.

## What moves from legacy code

- `api/dashboard/organisation/`, `api/dashboard/campus/`, `api/dashboard/college/`, `api/dashboard/location/`, `api/dashboard/zonal/`, `api/dashboard/district/`, `api/dashboard/affiliation/`, `api/dashboard/community_partner/`
- `mu_celery/org_aggregates_cron.py`

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Chapter-path prefix matching.
- The aggregate columns match a recompute.

## Open questions

- The chapter rollout plan (one state first) and how existing organisations map to chapter paths.
