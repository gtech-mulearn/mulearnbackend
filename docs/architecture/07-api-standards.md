# API standards

The rules for every new endpoint, and the compatibility promise for existing ones. The decisions are [ADR-010](adr/ADR-010-api-contract-envelope.md), [ADR-036](adr/ADR-036-rate-limiting.md), [ADR-044](adr/ADR-044-api-standards-v1-2.md) and [ADR-045](adr/ADR-045-hot-path-serialization.md).

**Status at `dev` 7fd66060.** The envelope `{hasError, statusCode, message, response}` exists (`utils/response.py` `CustomResponse`). Nothing else on this page exists yet. In particular:
- there is no `code` or `requestId`;
- there is no single exception handler;
- there are no project-wide throttles;
- `openapi.yaml` is hand-kept and stale.

## The compatibility promise

Old mobile builds stay installed for months, and the dashboard and the Discord bot depend on today's API. So:

- **`/api/v1` changes are additive only.** A field may be added. Removing or renaming a field, retyping it, changing a status code, or adding a required request field is a breaking change. CI blocks breaking changes unless an ADR and a deprecation period are in place.
- **The envelope keeps its four fields.** It gains two: `code` and `requestId`.
- **Token failures keep returning 401 or 403 with `statusCode 1000`,** because old builds refresh their token on both.
- **The token claims `id`, `muid`, `expiry` and `roles` stay** in tokens. Clients read them. The backend never authorizes from `roles` ([ADR-007](adr/ADR-007-scoped-grants-and-policies.md)).
- **Requests are compatible too.**
  - Legacy serializers keep today's behaviour of rejecting unknown keys, which comes from a patch in `mulearnbackend/__init__.py`.
  - Module serializers ignore unknown keys and log them, so a newer client can send a new field to an older server.
- **Deprecation** uses `Deprecation` and `Sunset` headers, with at least 6 months' notice for first-party clients and 12 months for partners.
- **App versions.** New app builds send `X-App-Version: <platform>/<semver>`. Below the minimum supported version, the API answers `426` with `code: platform.upgrade_required`, but only while the `platform.app_version_gate` flag is on. A request without the header is treated as a legacy build and allowed.
- **`/api/v2`** is used only for a redesign that can't be expressed additively.

## Routes and naming

- **Paths.** Module routes live under `/api/v1/<module>/…`, and service-client routes under `/api/v1/internal/<module>/…`.
- **Field names** are camelCase in JSON, and snake_case in Python.
- **Errors** name the field under its camelCase name.
- **Ids in URLs.** Internal sequential ids never appear in URLs or payloads. Public references are UUIDs, or `muid` for people.

## The response contract

**Success:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "code": "ok",
  "message": {"general": [], "fields": {}},
  "response": {
    "items": [{"eventId": "6f0c…", "title": "Hack Kerala", "startsAt": "2026-12-12T04:30:00Z"}],
    "nextCursor": "eyJpZCI6IjAxOTM2YjJlIn0"
  },
  "requestId": "req_01936b2e5b7e"
}
```

**Error:**

```json
{
  "hasError": true,
  "statusCode": 409,
  "code": "events.not_bookmarkable",
  "message": {"general": ["Cancelled or past events cannot be bookmarked."], "fields": {}},
  "response": {},
  "requestId": "req_01936b2e5b7f"
}
```

**Validation error:**

```json
{
  "hasError": true,
  "statusCode": 400,
  "code": "validation_error",
  "message": {"general": [], "fields": {"startsAt": ["Must be in the future."]}},
  "response": {},
  "requestId": "req_01936b2e5b80"
}
```

- **Every failure is a registered `DomainError`.** It is registered with `@error_code("<module>.<code>")`, which gives it a stable `code` and an HTTP status. One exception handler renders every error into the envelope, so a view never builds an error response by hand.
- **Codes are stable.** Removing or renaming a `code` is a breaking change.
- **Correct HTTP statuses** (404, 409, 422, 429 and so on) are adopted module by module, after the dashboard and app call sites are checked.
- **problem+json** (RFC 9457) rendering of the same error registry is deferred until the first partner or agent consumer.

## Pagination, filtering and sorting

- **New list endpoints use keyset pagination:** `?cursor=&limit=`, with `limit` at most 100, ordered by an indexed unique key. The response carries `nextCursor`, which is null on the last page.
- **Legacy endpoints keep `pageIndex` and `perPage`.** Their maximum page size (today `utils/utils.py` `MAX_PAGE_SIZE` = 1000) is reduced in steps, behind a flag, after the dashboard and app callers are checked.
- **Filters and sort fields are allowlisted** per selector. On new endpoints, an unknown parameter is a 400 that names it, through `building_blocks.api.query` `parse_query`.
- **No leading-wildcard `LIKE` across many columns on hot paths.** Search uses MySQL FULLTEXT first, and a search engine only on its trigger ([ADR-020](adr/ADR-020-search-on-trigger.md)).

```text
GET /api/v1/events/?cursor=eyJpZCI6IjAxOTM2YjJlIn0&limit=20&status=published&sort=startsAt
```

## Idempotency

- **POSTs that create or charge require an `Idempotency-Key` header** (a client-chosen UUID). A retry with the same key replays the first response instead of running twice.
  - Records are stored in `idempotency_record`.
  - Anonymous callers are keyed on `X-Device-Id`, or a hash of the client address.
  - Expired records are purged daily.
- **Commands that can be retried return `created=False` on a replay** ([04-module-rules.md](04-module-rules.md)).

```text
POST /api/v1/events/6f0c…/bookmarks/
Idempotency-Key: 3e1c9a8e-5d2b-4f7a-9a51-0c2e1b7f4d10
```

## Rate limiting

Limits run in two places ([ADR-036](adr/ADR-036-rate-limiting.md)):
- **at the edge** (Cloudflare or nginx), for volume and scrapers;
- **in the application,** for semantic limits such as OTP requests per identifier. A fixed-window limiter in `building_blocks` stores its state on the non-evicting `state` cache.

**Keys:**
- Authenticated callers are limited per user.
- Anonymous authentication flows are limited per normalised identifier and per device.
- An IP address serves only as a high ceiling, set above a campus burst. Hundreds of students behind one college NAT must not lock each other out.
- An audited **campus event mode** raises ceilings for listed campus networks during an event.

A limited request gets `429` with `code: rate_limited` and a `Retry-After` header.

## Caching headers

- **Public reads** send `Cache-Control: public, max-age=60, stale-while-revalidate=300` and an ETag, through `@public_cache()`.
- **Authenticated responses** default to `private, no-store`.

## Serialization on hot paths

- **List selectors** return `.values()` rows or small dataclasses, mapped to camelCase by a light read serializer ([ADR-045](adr/ADR-045-hot-path-serialization.md)). They do not use model serializers with `SerializerMethodField` queries per row.
- **Every list endpoint has a query-count test** at page size 1 and at the maximum page size. The two counts must be equal ([ADR-026](adr/ADR-026-performance-budgets-in-ci.md)).

## Exports and reports

Anything that scans more than one page runs as a `bulk` job. The result is a private file behind a signed URL, and the user is notified when it is ready. A CSV is never built on the request thread.

## API documentation

- **The spec is generated.** drf-spectacular builds it in CI; it is never edited by hand.
- **Breaking changes are gated.** An `oasdiff` check compares the spec with `dev`'s. It is report-only at first, then blocking.
- **`openapi.yaml` is replaced.** The hand-kept file is replaced by the generated spec once it covers every route.
