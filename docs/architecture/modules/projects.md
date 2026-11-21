# `projects`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Projects and impact projects: members, votes, comments, links, images and showcases.

## Kind

Supporting.

## Tables it owns

`projects`, `projects_comments`, `projects_votes`, `project_images`, `project_links`, `project_members`, `project_skill_link`, `impact_project`, `impact_project_link`, `impact_project_user_link`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `impact_project` | `api/dashboard/ig/impact_project_view.py` :: `patch`<br>`api/dashboard/ig/impact_project_view.py` :: `post` | — |
| `impact_project_link` | `api/dashboard/ig/impact_project_view.py` :: `_sync_links` | — |
| `impact_project_user_link` | `api/dashboard/ig/impact_project_view.py` :: `patch`<br>`api/dashboard/ig/impact_project_view.py` :: `post` | — |
| `project_images` | `api/dashboard/projects/projects_view.py` :: `post`<br>`api/dashboard/projects/projects_view.py` :: `put` | — |
| `project_links` | `api/dashboard/projects/projects_view.py` :: `_replace_links` | — |
| `project_members` | `api/dashboard/projects/projects_view.py` :: `delete`<br>`api/dashboard/projects/projects_view.py` :: `post` | — |
| `project_skill_link` | `api/dashboard/projects/projects_view.py` :: `_replace_skills` | — |
| `projects` | `api/dashboard/projects/projects_serializer.py` :: `create`<br>`api/dashboard/projects/projects_serializer.py` :: `update`<br>`api/dashboard/projects/projects_view.py` :: `delete`<br>`api/dashboard/projects/projects_view.py` :: `patch`<br>`api/dashboard/projects/projects_view.py` :: `post`<br>`api/dashboard/projects/projects_view.py` :: `put` | — |
| `projects_comments` | `api/dashboard/projects/projects_view.py` :: `delete`<br>`api/dashboard/projects/projects_view.py` :: `post`<br>`api/dashboard/projects/projects_view.py` :: `put` | — |
| `projects_votes` | `api/dashboard/projects/projects_view.py` :: `delete`<br>`api/dashboard/projects/projects_view.py` :: `post` | — |

## Public API (public.py)

`projects_of(user_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `projects.project_published` | none |

## Allowed dependencies

`communities.public`, `people.public`, `identity_access.public`.

## What moves from legacy code

`api/dashboard/projects/`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Update and delete are allowed only to the project owners, through a policy.

## Open questions

None yet.
