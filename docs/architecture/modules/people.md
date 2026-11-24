# `people`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Profiles, settings, socials, onboarding, consent records, age, the home chapter path, and data-principal rights (export, correction, erasure).

## Kind

Supporting.

## Tables it owns

- `user` (profile columns, plus `home_path` later), `socials`, `user_settings`, `user_domains`, `user_endgoals`
- new: consent records
- `forgot_password` moves to the authserver

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `forgot_password` | `api/dashboard/user/dash_user_views.py` :: `post` | — |
| `socials` | `api/dashboard/mentor/mentor_views.py` :: `patch`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/profile/profile_serializer.py` :: `update`<br>`api/dashboard/profile/profile_view.py` :: `put`<br>`api/register/serializers.py` :: `create` | Discord bot |
| `user` | `api/dashboard/profile/profile_serializer.py` :: `update`<br>`api/dashboard/profile/profile_view.py` :: `delete`<br>`api/dashboard/profile/profile_view.py` :: `post`<br>`api/dashboard/user/dash_user_serializer.py` :: `update`<br>`api/dashboard/user/dash_user_views.py` :: `delete`<br>`api/dashboard/user/dash_user_views.py` :: `patch`<br>`api/register/serializers.py` :: `create`<br>`mu_celery/task.py` :: `onboard_user` | Discord bot, authserver |
| `user_domains` | `api/register/register_views.py` :: `post` | — |
| `user_endgoals` | `api/register/register_views.py` :: `post` | — |
| `user_settings` | `api/dashboard/mentor/persona_views.py` :: `get`<br>`api/dashboard/mentor/persona_views.py` :: `post`<br>`api/dashboard/profile/profile_serializer.py` :: `update`<br>`api/dashboard/profile/profile_view.py` :: `post`<br>`api/register/serializers.py` :: `create` | — |

## Public API (public.py)

`profile_of(muid)`, `attribution_for(user_ids)`, `display_names(user_ids)`, `provision_member(...)` (the authserver's contract), `request_erasure(principal)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `people.user_registered`, `profile_updated`, `home_chapter_changed`, `social_link_verified`, `user_anonymised` | `organizations.organization_membership_changed` (recompute the home path) |
| `user.registered_via_invite` (integration event for `mucoin-service`, from Phase 3) | |

## Allowed dependencies

`identity_access.public`.

## What moves from legacy code

- `api/register/` (signup)
- `api/dashboard/profile/` and `api/dashboard/user/`

## Cut-over steps

1. [Epic: Phase 7: people and privacy](../github-issues/epics/phase-7-people-and-privacy.md)

## Tests this module needs

- A signup records consent (Phase 7).
- Erasure blanks personal columns and keeps ledger rows.
- No event payload carries a personal field (the μCoin exception is on hold with the integration).

## Open questions

- The legal design for minors is pending counsel ([ADR-052](../adr/ADR-052-privacy-minors-erasure.md)).
