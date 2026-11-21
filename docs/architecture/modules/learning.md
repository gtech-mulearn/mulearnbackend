# `learning`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The task catalogue: tasks, task types, skills and task reports, and which tasks are visible in which scope.

## Kind

Supporting.

## Tables it owns

`task_list` (gaining `scope_path` later), `task_type`, `task_skill_link`, `skill`, `task_report`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `skill` | `api/dashboard/skill/skill_views.py` :: `delete`<br>`api/dashboard/skill/skill_views.py` :: `post`<br>`api/dashboard/skill/skill_views.py` :: `put` | — |
| `task_list` | `api/dashboard/company/task_views.py` :: `delete`<br>`api/dashboard/company/task_views.py` :: `patch`<br>`api/dashboard/company/task_views.py` :: `post`<br>`api/dashboard/company/task_views.py` :: `put`<br>`api/dashboard/events/task_views.py` :: `patch`<br>`api/dashboard/events/task_views.py` :: `post`<br>`api/dashboard/mentor/task_views.py` :: `delete`<br>`api/dashboard/mentor/task_views.py` :: `post`<br>`api/dashboard/mentor/task_views.py` :: `put`<br>`api/dashboard/task/dash_task_view.py` :: `delete`<br>`api/dashboard/task/dash_task_view.py` :: `patch`<br>`api/dashboard/task/dash_task_view.py` :: `post`<br>`api/dashboard/task/dash_task_view.py` :: `put` | — |
| `task_report` | `api/dashboard/task_report/serializers.py` :: `update` | Discord bot |
| `task_skill_link` | `api/dashboard/company/task_views.py` :: `_save_task_skills`<br>`api/dashboard/mentor/task_views.py` :: `_save_task_skills`<br>`api/dashboard/task/dash_task_view.py` :: `_save_task_skills` | — |
| `task_type` | `api/dashboard/task/dash_task_serializer.py` :: `create`<br>`api/dashboard/task/dash_task_serializer.py` :: `update`<br>`api/dashboard/task/dash_task_view.py` :: `delete`<br>`api/dashboard/task/dash_task_view.py` :: `post`<br>`api/dashboard/task/dash_task_view.py` :: `put` | — |

## Public API (public.py)

`task_snapshot(task_id or hashtag)`, which `contributions` copies when it decides, and `visible_tasks(home_path, igs)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `learning.task_published`, `task_retired` | none |

## Allowed dependencies

`communities.public`, `organizations.public`, `identity_access.public`.

## What moves from legacy code

`api/dashboard/task/`, `api/dashboard/skill/`, `api/dashboard/task_report/`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- A task snapshot taken at approval time does not change when the task is edited later.

## Open questions

- How task visibility by scope path is introduced without hiding tasks from existing users.
