# Contributing to the architecture

How to add code without breaking the architecture, how decisions are made, and who reviews what. The rules themselves are in [04-module-rules.md](04-module-rules.md). This page is the "how".

Most of what this page describes arrives with the Phase 0 and Phase 1 issues: the local environment (issue 0004), the safe test runner (0002), the module generator (0023) and the base views (0026). Until those land, work on the issues in [github-issues/](github-issues/README.md) in dependency order.

## Getting started

When issues 0002 and 0004 have landed:

```sh
git clone https://github.com/gtech-mulearn/mulearnbackend.git && cd mulearnbackend
cp .env.sample .env                                 # read by commands you run on the host, such as scripts/test.sh
cp .env.local.example .env.local                     # read by the containers
pip install -r requirements.txt -r requirements-dev.txt
docker compose -f docker-compose.local.yml up -d   # MySQL from schema/latest.sql, two Redis, web, worker, beat, relay
scripts/test.sh tests/                              # the SQLite tier's new tests; must pass on a fresh clone
scripts/test.sh --mysql tests/                      # the MySQL tier against the local test_mulearn
```

- **Local database.** The local MySQL is built from the vendored `schema/latest.sql`. You never need access to `db-scripts`, production or the shared development database.
- **The API** is on `http://localhost:8000/api/v1/`.
- **Before then,** use the safe test commands in [github-issues/README.md](github-issues/README.md#safe-test-commands).

## Golden path: add an endpoint

The running example is a feature in the `events` module: **learners bookmark events**. If the module doesn't exist yet, create it first (see [Create a module](#create-a-module)).

**1. Domain rule and error**, in `modules/events/domain/`:

```python
# domain/errors.py
from building_blocks.errors import Conflict, NotFound, error_code


@error_code("events.not_bookmarkable", title="Event not bookmarkable")
class NotBookmarkable(Conflict):
    public_message = "Cancelled or past events cannot be bookmarked."


@error_code("events.event_not_found", title="Event not found")
class EventNotFound(NotFound):
    public_message = "Event not found."


# domain/rules.py
def check_bookmarkable(*, status: str, ends_at, now) -> None:
    if status == "cancelled" or ends_at <= now:
        raise NotBookmarkable()
```

**2. Policy**, in `modules/events/policies.py`. It looks at one grant at a time:

```python
from building_blocks.authz.core import GLOBAL_SCOPE, policy


@policy("events.bookmark")
def can_bookmark(grant, _event=None) -> bool:
    return grant.allows("events.bookmark", (GLOBAL_SCOPE, ""))
```

**3. Command**, in `modules/events/services/bookmarks.py`. It runs one transaction: authorization first, then the rule, the write and the event.

```python
from building_blocks import clock
from building_blocks.authz.core import Principal, require
from building_blocks.ids import uuid7_str
from building_blocks.messaging import outbox
from building_blocks.persistence.command import command
from modules.events.contracts import BookmarkResult, EventBookmarked
from modules.events.data.models import EventBookmarkRow, EventRow
from modules.events.domain.errors import EventNotFound
from modules.events.domain.rules import check_bookmarkable


@command(owner="events")
def bookmark_event(*, principal: Principal, event_id: str) -> BookmarkResult:
    require(principal, "events.bookmark")
    event = EventRow.objects.select_for_update().filter(id=event_id).first()
    if event is None:
        raise EventNotFound()
    check_bookmarkable(status=event.status, ends_at=event.ends_at, now=clock.now())
    row, created = EventBookmarkRow.objects.get_or_create(      # backed by UNIQUE(event_id, user_id)
        event_id=event_id, user_id=principal.user_id, defaults={"id": uuid7_str(), "created_at": clock.now()})
    if created:
        outbox.publish(EventBookmarked(aggregate_type="event", aggregate_id=event_id, user_id=principal.user_id))
    return BookmarkResult(bookmark_id=row.id, created=created)
```

**4. View**, using `@idempotent`, so a client retry with the same `Idempotency-Key` replays the first answer:

```python
from building_blocks.api import MuLearnAPIView
from building_blocks.api.idempotency import idempotent
from modules.events.services.bookmarks import bookmark_event


class BookmarkEventView(MuLearnAPIView):
    """POST /api/v1/events/<event_id>/bookmarks/ (send an Idempotency-Key header)."""

    @idempotent
    def post(self, request, event_id):
        result = bookmark_event(principal=request.principal, event_id=str(event_id))
        return self.ok({"bookmarkId": result.bookmark_id}, status=201 if result.created else 200)
```

**5. Tests:**
- in `tests/domain/`: the rule refuses cancelled and past events;
- in `tests/services/`: two calls create one row and publish one event, and a caller without the permission gets `Forbidden`;
- in `tests/api/`: the authorization matrix (anonymous 401, signed in 201, the same call again 200, a cancelled event 409 with `code == "events.not_bookmarkable"`).

For a **read endpoint,** write a selector that returns DTOs with keyset pagination, plus a query-count test at page sizes 1 and the maximum ([07-api-standards.md](07-api-standards.md)).

**Checklist for an endpoint:**
- [ ] The right base view (`MuLearnAPIView`, `PublicAPIView` with a reason and an allowlist line, or `InternalAPIView` with a scope).
- [ ] Writes go through one `@command`; POSTs that create something use `@idempotent`.
- [ ] A policy is registered and `require()` is called, unless the endpoint reads only the caller's own data.
- [ ] Errors are registered `DomainError`s.
- [ ] The module page in [modules/](modules/README.md) is updated.

## Golden path: add a background job

1. **Write the task** in the module's `tasks.py`. It is one line into a service, routed to a named queue, with time limits.
2. **For periodic work,** declare the schedule with `@scheduled`. Every run claims `(schedule, slot)` first, so a second beat runs nothing twice.
3. **Make it idempotent.** It may run twice.
4. **Never pass a long `eta` or `countdown`.** Store a due row and let a scheduled task pick it up.
5. **Test the service directly,** with a fixed clock.

The rules are in [05-events-and-background-work.md](05-events-and-background-work.md#queues-and-workers).

## Golden path: add an event

1. **Declare the event** in the producer's `contracts.py`, with `EVENT_TYPE`, `VERSION` and `PRODUCER`, and payload fields that are ids and facts only.
2. **Publish it inside the command** that makes it true, with `outbox.publish(...)`.
3. **Consume it** with `@subscribe(EventClass)` and `@consumer("<module>.<purpose>", queue=...)` in the consumer's `tasks.py`. The consumer calls a service that uses its own idempotency key for the fact.
4. **Document it** on both modules' pages.

The examples and rules are in [05-events-and-background-work.md](05-events-and-background-work.md#examples).

## Golden path: change the schema

1. **Say what you need in the issue,** with the exact DDL: the table, the columns, the indexes and whether it is an expand or a contract change.
2. **A maintainer writes the alter** in `db-scripts` and applies it, after review and a rehearsal. Contributors never apply DDL and never choose alter numbers.
3. **Update the model.** In your pull request, update the `managed = False` model in the owning module's `data/models.py` and its tests.
4. **Refresh the schema copy.** A maintainer refreshes `schema/latest.sql`. Your pull request merges after the alter is applied.
5. **Expand, then contract.** A column is dropped only by a later contract alter, at least one release after the last code that used it.

A **new value in a coded column** is a schema change too:
- for an `ENUM`, append the value to the end of the list, never reorder;
- for a `VARCHAR` with a `CHECK`, widen the `CHECK`.

## Golden path: add a permission

1. **Name the action** `<module>.<action>`.
2. **Register a policy** in the module's `policies.py`. It looks at one grant at a time and never combines roles.
3. **Give the permission to roles** in the role catalogue (`identity_access`).
4. **Call `require(principal, action, resource=...)`** in the command.
5. **Add rows to the authorization test matrix:** each role, with the same scope, a parent scope, a sibling scope and none.

Authorization code needs two reviewers (`core-review`).

## Create a module

1. **Generate it:** `python manage.py new_module <name>` creates the layout from [04-module-rules.md](04-module-rules.md#the-anatomy-of-a-module), an empty policy file, the test folders and its page in `docs/architecture/modules/`.
2. **Add the module** and its allowed dependencies to `tests/architecture/module_graph.toml`. CI fails if this creates a cycle.
3. **Mount its routes** in `modules/urls.py` with one `path("<name>/", include("modules.<name>.api.urls"))` line.
4. **Move its first table** from legacy `db/` in its own pull request, when the module needs one. That needs architecture review (below). A module may start with only routes or contracts; its tables move later.
5. **Add `"modules.<name>"` to `INSTALLED_APPS`.** The generator never edits shared files, so steps 2, 3 and 5 are yours.

## How decisions are made

**Architecture decision records** live in [adr/](adr/README.md).

**Write an ADR when a change:**
- alters a rule in [04-module-rules.md](04-module-rules.md);
- adds a runtime dependency, a datastore or a deployment role;
- changes a public API contract or an event contract;
- changes a module boundary or table ownership;
- changes how authentication, authorization, the karma ledger or payments work.

**How it works:**
- **Proposing.** Copy an existing record, take the next number, set the status to `Proposed`, and open a pull request that contains only the record. An accepted record is never edited: a new record supersedes it.
- **Decided by the module owner:** anything inside one module that keeps its public surface (internal refactors, selectors, new endpoints in its own namespace, its own tables' indexes).
- **Needs architecture review:**
  - new modules;
  - a table moving between modules;
  - a new module-graph edge;
  - a new event type or a breaking event version;
  - a new building block;
  - any change on the money, authorization, ledger, outbox or deploy paths;
  - any new infrastructure component.

## Reviews

- **Every pull request needs one approving review.** Pull requests labelled `core-review` need two, one from a maintainer: money, roles and authentication, the ledger, the outbox and relay, and deploy or rollout.
- **Enforcement.** Until `CODEOWNERS` and the branch rules are in place (issues 0028 and 0029), this is project policy, applied by maintainers when they merge.
- **What reviewers check:**
  - the rules in [04-module-rules.md](04-module-rules.md);
  - the issue's acceptance criteria;
  - that tests use the safe commands;
  - that the module page and any affected ADRs are updated in the same pull request.

## Branches and pull requests

- **Branch from `dev`,** and name the branch for the change: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
- **One change per pull request.** The title says, in the imperative, what changes. The description links the issue, lists the tests run, and notes any schema change it needs.
- **Never merge into `production` directly.** Releases are promoted by image digest ([12-testing-and-quality-gates.md](12-testing-and-quality-gates.md#release-strategy)).

## Repository files that support this

Phase 0 and Phase 1 issues add the files contributors expect:
- `CONTRIBUTING.md` and `DEVELOPMENT.md` (issue 0008);
- `CODEOWNERS` (issue 0028);
- issue and pull-request templates that follow [github-issues/README.md](github-issues/README.md).

The existing templates in `.github/ISSUE_TEMPLATE/` stay for bug and feature reports.
