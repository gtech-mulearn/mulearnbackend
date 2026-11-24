# `identity_access`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The role catalogue, scoped grants and their verification, and the grant resolver behind every authorization decision. A user may hold any number of grants at once ([ADR-007](../adr/ADR-007-scoped-grants-and-policies.md)). Token validation stays in `building_blocks.auth`.

## Kind

Supporting. The bottom of the module graph.

## Tables it owns

- `role`
- `user_role_link`, which becomes scoped grants by gaining `scope_type`, `scope_id`, `status` and `granted_by` through an expand alter
- `dynamic_role`, `dynamic_user`
- `mentor_scope_grant`, merged into grants later

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `dynamic_role` | `api/dashboard/dynamic_management/dynamic_management_serializer.py` :: `create`<br>`api/dashboard/dynamic_management/dynamic_management_serializer.py` :: `update`<br>`api/dashboard/dynamic_management/dynamic_management_view.py` :: `patch`<br>`api/dashboard/dynamic_management/dynamic_management_view.py` :: `post` | — |
| `dynamic_user` | `api/dashboard/dynamic_management/dynamic_management_serializer.py` :: `create`<br>`api/dashboard/dynamic_management/dynamic_management_serializer.py` :: `update`<br>`api/dashboard/dynamic_management/dynamic_management_view.py` :: `patch`<br>`api/dashboard/dynamic_management/dynamic_management_view.py` :: `post` | — |
| `mentor_scope_grant` | `api/dashboard/company/company_views.py` :: `_deactivate_company`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/mentor/dash_mentor_helper.py` :: `reconcile_mentor_ig_grants`<br>`api/dashboard/mentor/mentor_views.py` :: `delete`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/roles/dash_roles_views.py` :: `delete`<br>`mu_celery/mentor_tasks.py` :: `expire_stale_grants` | — |
| `role` | `api/dashboard/campus/dash_campus_helper.py` :: `assign_ig_campus_lead`<br>`api/dashboard/campus/events_views.py` :: `post`<br>`api/dashboard/campus/serializers.py` :: `create`<br>`api/dashboard/ig/dash_ig_view.py` :: `delete`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/ig/dash_ig_view.py` :: `post`<br>`api/dashboard/ig/dash_ig_view.py` :: `put`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `update`<br>`api/dashboard/roles/dash_roles_views.py` :: `delete` | Discord bot |
| `user_role_link` | `api/dashboard/campus/campus_views.py` :: `delete`<br>`api/dashboard/campus/campus_views.py` :: `post`<br>`api/dashboard/campus/dash_campus_helper.py` :: `assign_ig_campus_lead`<br>`api/dashboard/campus/events_views.py` :: `delete`<br>`api/dashboard/campus/events_views.py` :: `post`<br>`api/dashboard/campus/serializers.py` :: `create`<br>`api/dashboard/company/serializers.py` :: `save`<br>`api/dashboard/company/serializers.py` :: `update`<br>`api/dashboard/ig/dash_ig_view.py` :: `patch`<br>`api/dashboard/manage_interns/interns_views.py` :: `delete`<br>`api/dashboard/manage_interns/interns_views.py` :: `post`<br>`api/dashboard/manage_interns/serializers.py` :: `_assign_role`<br>`api/dashboard/manage_interns/serializers.py` :: `update`<br>`api/dashboard/mentor/mentor_views.py` :: `delete`<br>`api/dashboard/mentor/serializers.py` :: `create`<br>`api/dashboard/mentor/serializers.py` :: `update`<br>`api/dashboard/profile/profile_view.py` :: `patch`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/roles/dash_roles_views.py` :: `delete`<br>`api/dashboard/roles/dash_roles_views.py` :: `patch`<br>`api/dashboard/user/dash_user_serializer.py` :: `create`<br>`api/dashboard/user/dash_user_serializer.py` :: `update`<br>`api/dashboard/user/dash_user_views.py` :: `delete`<br>`api/register/serializers.py` :: `create` | Discord bot |

## Invariants

- One active grant per (user, role, scope).
- Only verified grants authorize.
- The scope exists.
- Grant, verify and revoke are audited.
- A combination of grants never allows more than its parts (the union rule, checked by a property test).

## Public API (public.py)

| Commands | Queries |
|---|---|
| `request_role(principal, role, scope)` | `grants_for(user_id)` |
| `verify_grant(principal, grant_id)` | `holders_of(role, scope)` |
| `revoke_grant(principal, grant_id, reason)` | `acting_principal(discord_id, client_id)` |
| `grant_directly(principal, user_id, role, scope)` | |

Every command invalidates the user's grant cache on commit.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `identity_access.grant_changed` | `people.user_anonymised` → revoke every grant |

## Allowed dependencies

`building_blocks` only.

## What moves from legacy code

- `api/dashboard/roles/` and the role checks in `utils/permission.py`
- the 24 functions in 16 files that write `user_role_link` today, listed above

## Cut-over steps

The authorization core is built in `building_blocks` first (issue 0027). The module itself is Phase 5.

1. [0027](../github-issues/0027-authz-core.md): Add principals, grants and the policy registry (Phase 1)
1. [Epic: Phase 5: identity and access](../github-issues/epics/phase-5-identity-and-access.md)

## Tests this module needs

- A generated matrix of roles × actions × scope relations.
- The union property test, with at least 10,000 examples.
- A revoked grant stops authorizing within 1 s of commit, in every process.
- A shadow-mode report before each enforcement switch.

## Open questions

- How today's interest-group-scoped role links map to scope rows (an `ig` scope, one row per link).
