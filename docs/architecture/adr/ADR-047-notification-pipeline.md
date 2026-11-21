# ADR-047: One notification pipeline

Status: Accepted (new on 2026-11-21; staged)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. In-app and push notifications live in `api/notification/` and `api/push/`, and several views send email synchronously.

## Context

In-app, push and email notifications are sent from several places. Each place has its own dedupe,
delays and failure handling. Fan-out to 100,000+ users and chapter-wide broadcasts need batching,
budgets and quiet hours.

## Options considered

- **Per-feature senders.**
- **One `notifications` module fed by events.**
- **An external notification service:** a new processor and a residency question.

## Decision

- Domain events flow to `notifications` consumers, which:
  1. choose recipients by preference;
  2. write one `notification` row per user (in-app);
  3. write one `notification_delivery` row per channel.
- **Push** is sent in batches of 500 tokens. **Email** goes through the provider with a timeout.
- **Per-channel budgets** live on the state store, and fail closed for bulk campaigns.
- **Claim-first dedupe.** A UNIQUE row per (notification, channel, device) is inserted before
  sending.
- **Quiet hours** set `available_at` on the delivery row, and a beat sweep releases due rows, so
  no long broker delays are needed.
- **Templates** are Django templates with gettext, starting with English and Malayalam.

**Staging:**
- **Now:** claim-first dedupe and `available_at` delivery rows on the existing push path.
- **Later:** the full event-fed pipeline with preferences and i18n templates, once push is live and
  a second channel needs it.

### Refinements (2026-11-21)

- The push budget is a flag value derived from the API's headroom for the app opens a campaign causes, not a fixed rate. Large campaigns pre-scale or wait.

## Consequences

- One place handles budgets, quiet hours and dedupe.

## Revisit when

- Fan-out exceeds 1 million deliveries a day, which triggers the extraction review in
  [ADR-001](ADR-001-domain-oriented-modular-monolith.md).

## Related ADRs

[ADR-001](ADR-001-domain-oriented-modular-monolith.md), [ADR-042](ADR-042-background-work-celery.md), [ADR-043](ADR-043-redis-cache-and-state.md)
