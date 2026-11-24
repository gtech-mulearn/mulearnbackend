# `payments`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Donations: payment orders, verification, provider webhooks and receipts.

## Kind

Generic.

## Tables it owns

`donor`, `donation`; new `payment_webhook_event` with a `UNIQUE` provider event id.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `donation` | `api/donate/donate_serializer.py` :: `create`<br>`api/donate/views.py` :: `post` | — |
| `donor` | `api/donate/donate_serializer.py` :: `create`<br>`api/donate/views.py` :: `get_or_create_donor` | — |

## Public API (public.py)

`receipt(donation_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `payments.donation_captured` | provider webhooks (inbound HTTP, verified and idempotent on the provider event id) |

## Allowed dependencies

`people.public`.

## What moves from legacy code

`api/donate/`.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- A provider webhook delivered twice records one payment.
- New money columns are integer paise ([ADR-053](../adr/ADR-053-business-calendar-and-money.md)).

## Open questions

- When webhook-driven payments start (that triggers the money-column migration).
