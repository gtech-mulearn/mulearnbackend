# ADR-011: Object storage for files; stateless nodes

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: partly in place. Some images already go through the media worker to R2 (`R2_PUBLIC_BASE_URL` in `mulearnbackend/settings.py`); other files still use `FileSystemStorage` on the server's disk.

## Context

Files on a node's local disk diverge once a second node runs behind a balancer, and filesystem
calls on request paths add latency per serialized row. An image pipeline on Cloudflare R2 already
exists: a media worker validates content, caps sizes, re-encodes images and returns an object
key.

## Options considered

- **S3 plus CloudFront.**
- **Cloudflare R2 for everything:** S3-compatible, no egress fees, and the image pipeline already
  runs there.
- **A mixed setup:** two storage systems to operate.

## Decision

Use R2 for all files.

- **Images** go through the media worker. The backend issues short-lived, single-purpose upload
  tickets, and the worker verifies only those ([ADR-046](ADR-046-tokens-keys-service-clients.md)).
- **Other files** (imports, certificates, posters, receipts) use the django-storages S3 backend
  against R2.
  - Anything personal goes in a private bucket and is served through signed URLs.
- **Imports** run as `bulk` jobs, with size and row caps and safe XML parsing.
- **Models store object keys.** URLs are computed with no filesystem access.
- **Migration:** a one-time copy of existing media, with a URL compatibility shim.
- **Everything moves before the second node.** Every file served by more than one node moves to
  object storage before that node joins the balancer.
- **Cleanup never deletes live objects:**
  - unreferenced objects move to a `trash/` prefix, which a 30-day lifecycle rule empties;
  - every module registers its object-key columns in the unreferenced-keys query, and a CI test
    fails when a model adds a key column that isn't registered.

## Consequences

- Horizontal scaling is unblocked.
- A one-time media copy and URL compatibility work.

## Revisit when

- django-storages breaks on a future Django release (swap to a thin boto3 adapter).

## Related ADRs

[ADR-046](ADR-046-tokens-keys-service-clients.md), [ADR-049](ADR-049-deployment-platform-and-dr.md)
