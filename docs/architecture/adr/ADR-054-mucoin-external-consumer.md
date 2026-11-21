# ADR-054: μCoin is an external consumer of integration events

Status: Accepted, on hold (2026-11-21): no μCoin work is planned for now. The design stands; the issues that would build it aren't filed ([On hold](../github-issues/README.md#on-hold))
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. The dormant coin columns and tables (`wallet.coin`, `mucoin_activity_log`, `mucoin_invite_log`) exist; nothing emits events to `mucoin-service`.

## Context

μCoin and μStore are a closed-loop coin economy: partner-funded coin pools, milestone rewards and a
redemption store. They are built as a standalone service with its own repository, database and
deployment: [gtech-mulearn/mucoin-service](https://github.com/gtech-mulearn/mucoin-service). Backend
issue [#3175](https://github.com/gtech-mulearn/mulearnbackend/issues/3175) records the founder's decision:
- core emits signed domain events;
- the μCoin service consumes them;
- nothing ever flows back.

No μCoin code path may write karma, levels or rankings. If the service is down, core is unaffected,
and events queue until it returns.

#3175 planned a separate in-core events app (`mu_events/`) with its own outbox table and a Celery
beat dispatcher. This architecture already has one transactional outbox ([ADR-005](ADR-005-transactional-outbox.md)).
Two outboxes would mean two delivery mechanisms, two retry policies and two replay tools.

## Options considered

- **(a) The architecture overrides #3175:** coins move into core under `rewards`, with a coin ledger.
  This contradicts a founder decision and duplicates a service that already exists.
- **(b) `mucoin-service` is an external consumer of the architecture's outbox.** Core publishes three
  integration events through the one outbox, and a webhook delivery adapter posts them to the service.
- **(c) Keep #3175's `mu_events/` app next to the outbox:** two outboxes, each half-maintained.

## Decision

**Option (b).**

**Coins stay out of core.**
- The dormant `wallet.coin`, `mucoin_activity_log`, `mucoin_invite_log` and the referral coin debit
  are **frozen**. No new feature reads or writes them.
- `rewards` covers vouchers, coupons and referrals only.
- There is no coin ledger, no `spend_coins` command and no `CoinsSpent` event in core.

**Three integration events,** each published by the module that owns the fact:

| Event type | Published by | Trigger | Payload |
|---|---|---|---|
| `user.level_up` | `gamification` | A learner's level **increases**. Grit can lower a level, and a decrease is never sent. | `{"muid": str, "old_level": int, "new_level": int}` |
| `task.verified` | `contributions` | A submission reaches appraiser-approved | `{"muid": str, "task_hashtag": str, "task_id": str}` |
| `user.registered_via_invite` | `people` | A registration carries a μCoin invite code | `{"invitee_muid": str, "invite_code": str}` |

Each event is written to the outbox in the same transaction as the fact it reports
([ADR-041](ADR-041-transactions-and-consistency.md)). The service identifies people by `muid`, so these
three payloads carry it. They are the only events allowed to: the payload test that keeps personal
identifiers out of events ([ADR-052](ADR-052-privacy-minors-erasure.md)) lists them explicitly.

**Delivery.** A webhook delivery adapter in `building_blocks/messaging` subscribes to these three
event types and keeps the contract #3175 defines:
- `POST {MUCOIN_URL}/api/v1/events/ingest` with body `{"payload": {...}}`;
- headers `Content-Type: application/json`, `X-Mu-Event-Id` (the outbox event id), `X-Mu-Event-Type`,
  and `X-Mu-Signature: sha256=<hex HMAC-SHA256 of the raw body>`, signed with `MUCOIN_WEBHOOK_SECRET`.

| Response | Adapter action |
|---|---|
| `200` processed, `200` duplicate, `202` ignored | Mark delivered |
| `400` or `401` | Dead letter and alert; never retried blindly |
| `5xx` or timeout | Retry with exponential backoff |

Delivery is at-least-once, and ordering is not required: the service is idempotent on
`X-Mu-Event-Id`. After the last retry, a delivery goes to a dead letter. The outbox's replay
command re-sends it.

**Tokens.** `mucoin-service` holds a ticket key and a webhook secret, never a token signing key
([ADR-046](ADR-046-tokens-keys-service-clients.md)). Until phase 2 of ADR-046 gives it the
authserver's JWKS, learner calls to the service use short-lived tickets minted by the backend. Each
ticket is an HMAC over the muid, the purpose and an expiry, with a key that only the backend (which
mints tickets) and `mucoin-service` hold.

**Acceptance.** Against a staging `mucoin-service`, the real adapter's first event returns
`processed` and the wallet balance becomes 3. Re-sending the same event id returns `duplicate`,
and the balance stays 3. This is #3175's 10-minute test.

## Consequences

- One outbox, one retry policy and one replay tool for every consumer, internal or external.
- The μCoin work in #3175 waits for the outbox (Phase 3) instead of landing a second mechanism first.
- The three events arrive in steps:
  - `user.registered_via_invite` with the outbox (Phase 3).
  - `task.verified` once approvals go through `contributions` (Phase 4). Today most approvals are written by the Discord bot directly in MySQL, so model signals in core would never see them.
  - `user.level_up` once `gamification` owns every level write (Phase 6). Today the bot and the scheduler change levels directly in MySQL.
- `mucoin-service` must accept the ticket scheme until JWKS exists. This changes how the
  service's current plan authenticates learners.
- The frozen coin tables stay in the schema until a later decision archives them.

## Revisit when

- Coins need to affect anything inside core (for example, gating a feature on a coin balance).
- A second external consumer needs a different delivery shape, such as a queue instead of a webhook.

## Related ADRs

[ADR-003](ADR-003-one-owner-per-table.md), [ADR-004](ADR-004-karma-ledger.md), [ADR-005](ADR-005-transactional-outbox.md), [ADR-035](ADR-035-cloudevents-envelope.md), [ADR-041](ADR-041-transactions-and-consistency.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
