# ADR-044: API standards v1.2 on DRF

Status: Accepted (new on 2026-11-21; extends ADR-010)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started.

## Context

All views are DRF `APIView` classes, and the conventions this ADR sets are built on DRF: the
envelope, the exception handler, the throttles and the idempotency decorator. Mobile builds stay installed for months.
The published OpenAPI spec has drifted from the code.

## Options considered

- **DRF for new modules.**
- **Django Ninja:** typed and faster, but a second framework for contributors, and the building
  blocks would be duplicated.

## Decision

| Concern | Rule |
|---|---|
| Errors | The envelope stays on `/api/v1`. Modules use correct HTTP statuses. Token failures keep their existing semantics while old builds exist. A problem+json (RFC 9457) rendering of the same error registry is deferred until the first partner or agent consumer. |
| Exports | Exports and reports that scan more than one page run as `bulk` jobs. The result is a private file behind a signed URL, with a notification when it is ready. |
| Token claims | Claims that clients read (`id`, `muid`, `expiry`, and `roles` as a UI hint) are part of the compatibility policy. The backend never authorizes from them. |
| Pagination | New list endpoints use keyset `?cursor=&limit=`, with a maximum of 100. Legacy page sizes are capped in steps, after client checks. |
| Filters and sorts | Every selector declares allowlists. New endpoints return 400 on unknown parameters. |
| Idempotency | `Idempotency-Key` is required on POSTs that create or charge. |
| Caching | Public reads send `Cache-Control: public, max-age=60, stale-while-revalidate=300` and an ETag. Private responses default to `no-store`. |
| Spec | drf-spectacular generates the spec in CI. An `oasdiff` gate blocks breaking changes without an ADR. |
| Deprecation | `Deprecation` and `Sunset` headers: at least 6 months for first-party clients, 12 months for partners. |
| App versions | New builds send `X-App-Version: <platform>/<semver>`. Below the minimum supported version (a `platform.*` setting, checked only while the
`platform.app_version_gate` flag is on), the API returns 426 with `platform.upgrade_required`. A request without the header is treated as a legacy build and allowed. |
| Request compatibility | Legacy serializers keep strict unknown-key handling. Module serializers ignore unknown keys and log them. |

### Refinements (2026-11-21)

- New endpoints validate input with the shared `parse_query(serializer, data)` and `parse_body(serializer, data)` from `building_blocks.api.query`; a parameter the serializer doesn't declare is a 400 that names it.
- For anonymous callers, idempotency records are keyed on `X-Device-Id` (else a hash of the client address), so a mobile retry from a new network is still recognised. Expired records are purged daily.
- problem+json, when it is turned on, is chosen by content negotiation inside the exception handler, so a success body is never rendered as a problem document.

## Consequences

- One framework for contributors.
- Old app builds keep working, and new builds can be told to upgrade.

## Revisit when

- More than 30% of new endpoints need features DRF lacks.

## Related ADRs

[ADR-010](ADR-010-api-contract-envelope.md), [ADR-041](ADR-041-transactions-and-consistency.md), [ADR-045](ADR-045-hot-path-serialization.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
