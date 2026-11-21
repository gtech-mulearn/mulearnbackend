# `integrations`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The anti-corruption layers for outside systems: Discord (the desired-state reconciler, role and channel sync, the bot heartbeat) and partner integrations.

## Kind

Generic.

## Tables it owns

`integration`, `integration_authorization`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `integration_authorization` | `api/integrations/kkem/kkem_serializer.py` :: `create_kkem_link`<br>`api/integrations/kkem/kkem_views.py` :: `patch`<br>`api/register/serializers.py` :: `create` | — |

## Public API (public.py)

`reconcile_discord(window)` (an operator command), `record_heartbeat(client, processed)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `integrations.discord_sync_requested` | `identity_access.grant_changed`, `gamification.level_changed`, `communities.ig_membership_changed`, `people.user_registered` |

## Allowed dependencies

`contributions.public`, `communities.public`, `people.public`, `identity_access.public`.

## What moves from legacy code

`api/integrations/` and `api/dashboard/discord_moderator/`.

## Cut-over steps

1. [0101](../github-issues/0101-bot-heartbeat-endpoint.md): Add the Discord bot heartbeat endpoint and metric (Phase 4)
1. [0102](../github-issues/0102-bot-sends-heartbeat.md): Send heartbeats from the Discord bot (Phase 4)
1. [0103](../github-issues/0103-bot-shadow-mode.md): Run the bot's karma path through the internal API in shadow mode (Phase 4)
1. [Epic: Phase 4: finish the contributions cut-over](../github-issues/epics/phase-4-contributions-cutover.md)

## Tests this module needs

- The reconciler converges a synthetic 2-hour gap within 15 minutes, driving the same commands the bot uses.
- The heartbeat alert fires within 10 minutes when processing stops.

## Open questions

- The Discord rate-limit budget the reconciler may use.
