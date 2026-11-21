# `careers`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Companies as employers, jobs, applications, the talent shortlist, the career lab, collaborations and problem statements.

## Kind

Supporting.

## Tables it owns

`company`, `company_admin_link`, `company_collaboration`, `company_event_template`, `company_feedback`, `company_job_rules`, `company_jobs`, `company_talent_shortlist`, `company_task_template`, `hiring`, `user_job_application`, `problem_statement`, `problem_statement_interaction`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `company` | `api/dashboard/company/company_views.py` :: `post`<br>`api/dashboard/company/serializers.py` :: `create`<br>`api/dashboard/company/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create` | — |
| `company_admin_link` | `api/dashboard/company/company_views.py` :: `_deactivate_company`<br>`api/dashboard/company/company_views.py` :: `delete`<br>`api/dashboard/company/company_views.py` :: `post` | — |
| `company_collaboration` | `api/dashboard/company/collaboration_views.py` :: `delete`<br>`api/dashboard/company/collaboration_views.py` :: `post` | — |
| `company_event_template` | `api/dashboard/company/event_template_views.py` :: `delete`<br>`api/dashboard/company/event_template_views.py` :: `post` | — |
| `company_feedback` | `api/dashboard/company/feedback_views.py` :: `post` | — |
| `company_job_rules` | `api/dashboard/company/job_serializers.py` :: `create`<br>`api/dashboard/company/job_serializers.py` :: `update` | — |
| `company_jobs` | `api/dashboard/company/job_serializers.py` :: `create`<br>`api/dashboard/company/job_serializers.py` :: `update`<br>`api/dashboard/company/job_views.py` :: `delete`<br>`api/dashboard/company/job_views.py` :: `post`<br>`mu_celery/company_tasks.py` :: `expire_stale_jobs` | — |
| `company_talent_shortlist` | `api/dashboard/company/mulearner_views.py` :: `delete`<br>`api/dashboard/company/mulearner_views.py` :: `post` | — |
| `company_task_template` | `api/dashboard/company/task_views.py` :: `delete`<br>`api/dashboard/company/task_views.py` :: `post` | — |
| `hiring` | `api/dashboard/career_lab/career_lab_serializers.py` :: `create`<br>`api/dashboard/career_lab/career_lab_serializers.py` :: `update`<br>`api/dashboard/career_lab/career_lab_views.py` :: `delete` | — |
| `problem_statement` | `api/dashboard/problem_statement/manage_views.py` :: `post`<br>`utils/problem_statement.py` :: `apply_changes`<br>`utils/problem_statement.py` :: `publish`<br>`utils/problem_statement.py` :: `unpublish` | — |
| `problem_statement_interaction` | `api/dashboard/problem_statement/learner_views.py` :: `delete`<br>`api/dashboard/problem_statement/learner_views.py` :: `put`<br>`api/dashboard/problem_statement/manage_views.py` :: `delete` | — |
| `user_job_application` | `api/dashboard/company/job_serializers.py` :: `create`<br>`api/dashboard/company/job_serializers.py` :: `update`<br>`api/dashboard/company/job_views.py` :: `delete` | — |

## Public API (public.py)

`company(company_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `careers.job_posted`, `job_expired`, `application_submitted` | none |

## Allowed dependencies

`organizations.public`, `people.public`, `identity_access.public`.

## What moves from legacy code

`api/dashboard/company/`, `api/dashboard/career_lab/`, `api/dashboard/problem_statement/`, `mu_celery/company_tasks.py`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- Job expiry runs once per slot.

## Open questions

None yet.
