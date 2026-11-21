# `administration`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Platform settings (the `platform.*` keys of `system_setting`) and the URL shortener.

## Kind

Generic.

## Tables it owns

`system_setting` (`platform.*` keys only; `auth.*` belongs to the authserver and `db.version` to the migration runner), `url_shortener`, `url_shortener_tracker`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `system_setting` | `api/dashboard/feature/feature_views.py` :: `post` | authserver |
| `url_shortener` | `api/url_shortener/serializers.py` :: `create`<br>`api/url_shortener/serializers.py` :: `update`<br>`api/url_shortener/url_shortener_view.py` :: `delete`<br>`api/url_shortener/url_shortener_view.py` :: `post`<br>`api/url_shortener/url_shortener_view.py` :: `put` | — |

## Public API (public.py)

`setting(key)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| none | none |

## Allowed dependencies

`identity_access.public`.

## What moves from legacy code

`api/dashboard/feature/`, `api/dashboard/dynamic_management/`, `api/url_shortener/`. Feature toggles move into the flag store ([ADR-031](../adr/ADR-031-feature-flags.md)).

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- A setting change is audited.

## Open questions

None yet.
