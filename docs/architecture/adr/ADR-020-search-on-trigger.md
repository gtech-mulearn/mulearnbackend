# ADR-020: MySQL FULLTEXT first; a search engine on trigger

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. List search ORs `icontains` filters across columns in the shared paginator helper in `utils/utils.py`.

## Context

People, college, event and task search does not scale with leading-wildcard `LIKE` across many
OR-ed columns on the primary.

## Options considered

- **MySQL FULLTEXT with the ngram parser,** on the hot search columns.
- **OpenSearch or Meilisearch now:** one more datastore to operate before it is needed.

## Decision

- Add FULLTEXT indexes with the ngram parser, through expand alters, on the hot columns: people
  name and muid, and organisation title.
- Selectors use them as each module moves, replacing OR-ed `icontains`.
- A dedicated search engine, chosen by an ADR at the time, is fed by events once the trigger
  fires.

## Consequences

- Search improves without new infrastructure.
- Ranking quality is limited until a search engine arrives.

## Revisit when

- Search p95 exceeds 300 ms, or search is more than 5% of primary load.

## Related ADRs

[ADR-019](ADR-019-read-scaling-and-connections.md), [ADR-044](ADR-044-api-standards-v1-2.md)
