# muLearn Backend — PR Review Rules

These rules exist to protect the architecture, security model, and data integrity of this
specific Django REST API. They are not generic Django advice. Enforce them when they apply,
explain the concrete failure when you flag something, and stay quiet otherwise. Prefer a few
accurate comments over many speculative ones.

---

## 1. Repository Overview

muLearn is the backend for a community learning platform. It exposes a JSON API consumed by
multiple frontends (web dashboard, mobile app, Discord bot, and partner integrations such as
KKEM, Wadhwani, and QSEverse).

Top-level layout:

- **`db/`** — every model in the system, split into per-domain files (`user.py`, `task.py`,
  `organization.py`, `events.py`, `hackathon.py`, `intern.py`, `mentor.py`, `projects.py`,
  `learning_circle.py`, `launchpad.py`, `donation.py`, etc.). This app owns the data layer only.
- **`api/`** — all views, grouped by feature area. `api/dashboard/<domain>/` holds the bulk of
  the admin/dashboard surface; each domain folder contains `*_views.py`, `*_serializer.py`, and
  `urls.py`. Other top-level API areas: `auth/`, `register/`, `integrations/`, `hackathon/`,
  `leaderboard/`, `notification/`, `protected/`, `launchpad/`, `donate/`, `calendar/`,
  `top100_coders/`, `url_shortener/`, `common/`.
- **`utils/`** — cross-cutting building blocks every view depends on: `response.py`
  (`CustomResponse`), `permission.py` (JWT + role decorators), `exception.py`, `karma.py`
  (karma/wallet business logic), `utils.py` (`CommonUtils`, `DateTimeUtils`, `DiscordWebhooks`,
  mail helpers).
- **`mu_celery/`** — Celery tasks and scheduled crons (intern status, deadlines, achievements).
- **`mulearnbackend/`** — project config: `settings.py`, `urls.py`, `middlewares.py`,
  `celery.py`, ASGI/WSGI/routing entrypoints.

Routing: `mulearnbackend/urls.py` mounts everything under `/api/v1/` via `api/urls.py`, which
fans out to each area's `urls.py`.

---

## 2. Detected Stack

- **Python / Django 4.2.7**, **DRF 3.14.0**.
- **Database: MySQL** (`mysqlclient`, `pymysql`). `CONN_MAX_AGE = 600`.
- **All models are `managed = False`.** The database schema is owned externally (see
  `schema.sql` and `alter-scripts/`). Django migrations are **not** the source of truth.
- **Auth: custom JWT (HS256, signed with `SECRET_KEY`)**, validated manually in
  `utils/permission.py`. `djangorestframework-simplejwt` is installed but the live path is the
  custom `CustomizePermission` / `JWTUtils`. Token *issuance* happens on a separate auth service
  (`AUTH_DOMAIN`); this backend primarily **validates** tokens.
- **Background: Celery 5.4 + Redis broker** (`redis://.../2`). Beat schedule defined in settings.
- **Cache: Redis** (`django_redis`) is the default cache; channels use `channels-redis`.
- **Async: Daphne / ASGI** (`channels`) for websocket routing.
- **API docs: drf-spectacular 0.27.2** — schema at `/api/schema/`, Swagger gated behind
  `ENABLE_SWAGGER`.
- **External services:** Razorpay (payments), Wadhwani, KKEM, QSEverse, Discord webhooks, SMTP email.
- **Config: `python-decouple`** (`decouple_config` / `.env`). Secrets never live in code.
- **Tests: pytest + pytest-django** with `APIClient` and `conftest.py` fixtures (currently only
  `projects/`, `mentor/`, `events/` are covered).

Rules must match this stack. Do not suggest tooling or patterns that aren't already here
(e.g. DRF ViewSets/routers, Alembic, dataclass DTOs, async views) unless fixing a proven bug.

---

## 3. Architecture Rules

- **Respect the `db/` ↔ `api/` ↔ `utils/` split.** Models live in `db/<domain>.py`, request
  handling in `api/<area>/`, shared helpers in `utils/`. Do not define models inside `api/`, and
  do not put HTTP/response logic in `db/`.
- **New endpoints follow the existing folder shape**: a `*_views.py`, a `*_serializer.py`, and a
  `urls.py` wired into the parent `urls.py`. Don't introduce a parallel structure.
- **This codebase deliberately does not use a service/repository layer.** Business logic lives in
  views and in focused `utils/` helpers (e.g. `utils/karma.py`). Do not recommend adding service
  classes, repositories, CQRS, or new abstraction layers. Reuse the existing helper instead.
- **Shared domain logic must be reused, not re-implemented.** Karma/wallet mutations go through
  `utils/karma.py` (`add_karma` / `remove_karma`). Pagination/search/sort go through
  `CommonUtils.get_paginated_queryset`. CSV export goes through `CommonUtils.generate_csv`. Email
  goes through `send_template_mail`. Flag any inline reimplementation of these.
- **Cross-module impact:** a `db/` model change is never local. Before approving, trace which
  serializers expose the field, which views/filters reference it, which Celery tasks read it, and
  which integration consumes it. Call out the affected API contracts explicitly.

---

## 4. Model Rules (`db/`)

- **All models are `managed = False` with an explicit `db_table`.** Any new model or field must
  exactly mirror the real database (`db_column`, `db_table`, types, nullability). A model change
  here does **not** alter the database — the corresponding schema change must land separately in
  `schema.sql` / `alter-scripts/`. Flag any model/field addition that has no matching schema
  artifact, and never assume `makemigrations`/`migrate` will apply it.
- **Primary keys are `CharField(max_length=36)` UUIDs** (`default=uuid.uuid4`). New tables follow
  this; do not introduce `AutoField`/integer PKs or change PK type on existing tables.
- **Audit columns follow a fixed pattern:** `created_by` / `updated_by` are FKs to `User` with
  `on_delete=models.SET(settings.SYSTEM_ADMIN_ID)` and an explicit `db_column`; `created_at` is
  `auto_now_add`, `updated_at` is `auto_now`. New tables that record actors must keep this
  pattern so the `SYSTEM_ADMIN_ID` fallback protects against user deletion. Don't use
  `on_delete=CASCADE` for `created_by`/`updated_by`.
- **`on_delete` choices encode real ownership.** `CASCADE` only where the child truly cannot
  outlive the parent; `SET_NULL` / `SET(SYSTEM_ADMIN_ID)` for audit/actor references. Question any
  change that flips this, because deletes propagate across a heavily interlinked schema.
- **Do not suggest adding indexes or constraints reflexively.** Indexes belong in the externally
  managed schema, not in `Meta` on an unmanaged model. Only raise an index if there is a concrete
  filter/order on a large table *and* note it must be added to the DB schema, not via Django.
- **Keep `choices` in sync with `utils/types.py` enums** (`RoleType`, `OrganizationType`,
  status enums, etc.). Magic strings that duplicate an existing enum value should reference the enum.

---

## 5. ORM / Performance Rules

- **`User.objects` excludes suspended users.** `ActiveUserManager` filters out
  `suspended_at`/`suspended_by`. Use `User.objects` for normal user-facing reads; use
  **`User.every`** when you must include suspended users (admin/management views, suspension
  workflows, FK integrity checks, lookups by id where the row may be suspended). Flag code that
  uses `User.objects` and then is surprised a known user "doesn't exist" — that is almost always a
  suspended-user bug.
- **List endpoints must `select_related` / `prefetch_related` everything the serializer touches.**
  This API serializes deep relations (e.g. `org.district.zone.state.country`, wallet/level links,
  role links). A list view that serializes a related field without prefetching it produces one
  query per row. State the exact field and the per-row cost when flagging.
- **Watch for N+1 hidden inside `SerializerMethodField`.** Several serializers run queries
  per-object inside method fields (e.g. resolving roles, dynamic types, company org). When a new
  method field issues a query, require it to be backed by a prefetch or annotation on the queryset.
- **Use `.exists()` / `.count()` / `values_list` instead of materializing full querysets** for
  presence and id checks — this is the established style (see `utils/karma.py`, the intern crons).
- **All list endpoints are paginated through `CommonUtils.get_paginated_queryset`** and returned
  via `CustomResponse(...).paginated_response(...)`. A new list endpoint that returns an unbounded
  queryset is a regression.

---

## 6. API / View Rules

- **Views are `APIView` subclasses with one method per HTTP verb.** Do not introduce DRF
  `ViewSet`s, routers, or generic views — they don't fit the response envelope or the per-method
  decorator pattern used everywhere here.
- **Every view returns a `CustomResponse`.** Use `get_success_response()`,
  `get_failure_response()`, `get_unauthorized_response()`, or `paginated_response()`. Never return
  a raw DRF `Response`, `JsonResponse`, or `HttpResponse` from an API view (the image endpoints via
  `ImageResponse` and CSV downloads are the only sanctioned exceptions). Breaking the
  `{hasError, statusCode, message, response}` envelope breaks every client.
- **Validation failures return `get_failure_response(...)` with a message**; they do not raise.
  Uncaught exceptions are logged and re-raised by `UniversalErrorHandlerMiddleware` — don't add
  bare `try/except: pass` that swallows errors and returns a fake success.
- **Status-code discipline:** success bodies use the success helper (HTTP 200); auth/permission
  denials use `get_unauthorized_response()` (403). Don't invent new shapes for these.
- **Keep views thin and consistent with siblings.** Reuse `CommonUtils`, `utils/karma.py`, mail
  helpers, and `DiscordWebhooks` rather than duplicating logic inline. Side effects that exist in
  sibling endpoints (e.g. firing `DiscordWebhooks.general_updates` after a mutation) should not be
  silently dropped in a new handler for the same resource.
- **Every endpoint is annotated with `@extend_schema(tags=[...], ...)`** for drf-spectacular. New
  endpoints must include it with the correct tag; otherwise the generated OpenAPI/`openapi.yaml`
  drifts from reality.

---

## 7. Serializer Rules

- **Serializers are `ModelSerializer` with explicit `fields` lists** — never `fields = "__all__"`.
  Adding a field to an existing serializer changes a published API contract: confirm the field is
  safe to expose and that clients can handle it.
- **Never expose sensitive columns.** `User.password`, raw tokens, `ForgotPassword` internals, and
  similar must never appear in a serializer `fields` list or a method field. Flag any serializer
  that pulls these in.
- **Derived/related data uses `SerializerMethodField` or `source=` traversal** (the existing
  convention). Keep query-bearing method fields backed by a prefetch (see §5).
- **Multi-write serializer logic must be wrapped in `transaction.atomic`** (the established pattern
  for create/update that touches several tables). A multi-step write without a transaction risks
  partial writes across the interlinked schema.
- **Don't bury authorization or heavy business rules inside serializers.** Permission and role
  decisions belong in the view layer (decorators / `JWTUtils`), not in `validate_*`.

---

## 8. Security Standards

- **Authentication is `authentication_classes = [CustomizePermission]`.** Any new endpoint that is
  not deliberately public must declare it. A view that reads user data without an auth class is a
  data-leak bug — flag it as CRITICAL.
- **Authorization is enforced with the role decorators**: `@role_required([RoleType.X.value])`,
  `RoleRequired`, or `@dynamic_role_required(type)`. Service-to-service endpoints use
  `BackendApiKeyPermission` (the `Api-Key` header). A mutating or admin endpoint with no role/key
  check is a privilege-escalation risk.
- **Trust the JWT, never the request body, for identity and roles.** Always derive the actor via
  `JWTUtils.fetch_user_id` / `fetch_muid` / `fetch_role`. Code that reads `user_id`, `roles`, or
  `admin` from `request.data`/query params to make an authorization or ownership decision is a
  bypass — flag it. (Note the existing `request.data["admin"] = JWTUtils.fetch_user_id(request)`
  pattern overrides client input with the trusted id; preserve that direction.)
- **Object-level ownership must be checked explicitly.** Role checks alone don't prove the actor
  owns the record being mutated/read. For per-user resources, confirm the row belongs to the
  JWT user (or an authorized role) before returning or modifying it.
- **Secrets come only from `decouple_config`.** No hardcoded keys, tokens, or credentials.
  `SECRET_KEY` doubles as the JWT signing key — never log it, return it, or weaken the HS256
  verification (`verify=True`, explicit `algorithms=["HS256"]`).
- **Be deliberate about the permissive defaults.** `CORS_ALLOW_ALL_ORIGINS = True` and
  `debug_toolbar` are present; do not widen exposure further (e.g. don't add `DEBUG=True` defaults,
  don't print/log request bodies containing credentials, don't echo upstream secrets in responses).
- **Don't leak internals in error messages.** Returning `str(e)` is used in places, but new code
  should avoid surfacing stack traces, SQL, or upstream secret-bearing payloads to clients.

---

## 9. External Integration Rules

- **Every outbound `requests` call must set `timeout=` and handle failure.** This is a real,
  recurring gap in the codebase — many calls have no timeout, so a slow upstream (Wadhwani, KKEM,
  QSEverse, Razorpay, Discord) can hang a worker. The auth proxy (`api/auth/auth_views.py`) is the
  reference pattern: `timeout=30` plus explicit `requests.exceptions.Timeout` /
  `RequestException` handling returning a `CustomResponse` failure. Require this for any new or
  modified external call.
- **Never call `response.json()` without guarding for non-JSON / error payloads.** Check status and
  shape before indexing into the response.
- **Payment (Razorpay) flows must verify signatures and treat secrets as confidential.** Don't log
  payment payloads or secrets; don't trust client-reported payment status without server-side
  verification.
- **`DiscordWebhooks.general_updates` and email sends are side effects** — a failure there should
  not corrupt the primary transaction or mask the real result. Keep them after the core write.

---

## 10. Migration & Schema-Change Safety

- Because models are `managed = False`, **schema changes are made in the database / `schema.sql` /
  `alter-scripts/`, not through Django migrations.** A PR that adds a model field but no
  corresponding DB schema change will pass code review and then fail at runtime with an unknown
  column — flag the missing schema artifact.
- **Renaming/removing a field or table is a breaking change** across serializers, filters, raw
  references, and integrations. Require the cross-module trace (§3) and confirm backward
  compatibility for in-flight clients before approving.
- Confirm existing-data compatibility for any new non-null column (it must have a DB-level default
  or a backfill), since Django won't manage the column for you.

---

## 11. Background Jobs (Celery) Rules

- **Crons must be idempotent.** They run on a schedule (see `CELERY_BEAT_SCHEDULE`) and may
  reprocess overlapping windows — re-running must not double-apply karma, double-transition status,
  or duplicate rows. The intern crons (`mu_celery/intern_cron.py`) are the model: batch-fetch, set
  membership for O(1) lookups, and `save(update_fields=[...])` for narrow writes.
- **Use `update_fields` on targeted status writes** to avoid clobbering concurrently-changed
  columns.
- **There is no system-user convention for `updated_by` in crons** (documented limitation). Don't
  invent one ad hoc; leave actor columns unchanged in background jobs unless the team adds a
  convention.
- **Don't block the request path on slow work.** Long-running or external-API-heavy work belongs in
  a Celery task, not a synchronous view.
- **Bulk operations** (`bulk_create`, `F()` updates) are the established pattern for multi-row karma
  and wallet changes — prefer them over per-row loops for large sets, and keep wallet/karma changes
  consistent between `add_karma` and `remove_karma`.

---

## 12. Testing Expectations

- **Tests use pytest + pytest-django**, `APIClient`, and fixtures in a local `conftest.py`
  (`user_fixture`, `auth_client`, resource fixtures). Match this style; don't introduce
  `unittest.TestCase` or a new harness.
- **Require tests for:** permission/visibility rules (owner-vs-public access is the existing focus,
  see `projects/tests/`), karma/wallet mutations, serializer output contracts, and every bug fix
  (a regression test that fails before the fix).
- **Be aware `force_authenticate` bypasses `CustomizePermission`/JWT.** Tests for role-gated
  endpoints that rely on `JWTUtils.fetch_role` need a real signed token, not just
  `force_authenticate`. Flag a test that claims to cover a role check but never exercises the JWT
  path.
- **Do not demand tests for:** settings tweaks, schema/`alter-scripts` changes, `@extend_schema`
  doc-only edits, or cosmetic refactors.
- Test behavior (response envelope, visibility, side effects), not private implementation details.

---

## 13. Repository-Specific Anti-Patterns (flag these)

1. **Using `User.objects` where suspended users must be included** (admin lookups, suspension
   flows, FK checks). Use `User.every`.
2. **An outbound `requests` call with no `timeout=`** and no `Timeout`/`RequestException` handling.
3. **Returning a raw `Response`/`JsonResponse` from an API view** instead of `CustomResponse`.
4. **Adding a model field with no matching `schema.sql` / `alter-scripts` change** (relying on
   Django migrations on a `managed = False` model).
5. **Deriving identity/roles from `request.data` or query params** instead of `JWTUtils`.
6. **A new view missing `authentication_classes` and/or a role/key decorator** on non-public data.
7. **A list endpoint serializing related/method fields without `select_related`/`prefetch_related`**,
   or returning an unpaginated queryset.
8. **Re-implementing karma/wallet, pagination, CSV, or email logic inline** instead of reusing
   `utils/karma.py`, `CommonUtils`, or `send_template_mail`.
9. **`fields = "__all__"`** or exposing `password`/tokens/secrets in a serializer.
10. **Swallowing exceptions to fake a success response**, defeating `UniversalErrorHandlerMiddleware`.
11. **Hardcoded secrets/URLs** instead of `decouple_config`.
12. **A new endpoint without `@extend_schema`**, drifting the OpenAPI contract.

Note: duplicate `urlpatterns` entries mapping the same path to one view under different `name`s
(e.g. get/patch/delete for `<str:user_id>/`) are an intentional convention here — do **not** flag
them as duplicates.

---

## 14. PR Review Checklist

**CRITICAL (block):**
- [ ] No missing `authentication_classes` / role / `Api-Key` check on non-public data.
- [ ] No identity/role/ownership decision based on client-supplied input.
- [ ] No exposed secrets, passwords, or tokens (code, logs, serializers, responses).
- [ ] No model/field change lacking a corresponding DB schema change (`managed = False`).
- [ ] No response-envelope break that would regress clients.

**HIGH:**
- [ ] Correct `User.objects` vs `User.every` for the suspended-user case.
- [ ] Outbound `requests` have `timeout=` and failure handling.
- [ ] Karma/wallet, pagination, CSV, email reuse existing helpers and stay consistent.
- [ ] Crons remain idempotent and use `update_fields`.
- [ ] Cross-module impact (serializers, filters, integrations, tasks) accounted for.

**MEDIUM:**
- [ ] List endpoints prefetch what serializers touch; no introduced N+1; pagination intact.
- [ ] Serializers expose only intended fields; multi-write wrapped in `transaction.atomic`.
- [ ] Tests added for permission/visibility rules, business logic, and bug fixes.
- [ ] `@extend_schema` present and correctly tagged.

**LOW:**
- [ ] Naming, file placement, and enum usage (`utils/types.py`) match existing conventions.

When commenting, name the exact file, the affected workflow, and the concrete failure scenario.
Skip style nits and anything already consistent with the patterns above.
