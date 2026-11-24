# `analytics`

**Status:** deferred. This module owns no table until its trigger fires.

## Purpose

Dashboard read models for the home, campus, zonal and district dashboards.

## Kind

Generic, **deferred**. Trigger: the replica trigger in [ADR-019](../adr/ADR-019-read-scaling-and-connections.md) fires, or dashboard p95 exceeds 1 s.

## Tables it owns

None while deferred.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

None while deferred.

## Public API (public.py)

None while deferred.

## Events

None while deferred. When started, it consumes `contributions.karma_awarded` and membership events.

## Allowed dependencies

The public read APIs of every module.

## What moves from legacy code

None while deferred. The dashboards stay in their current `api/dashboard/` packages.

## Cut-over steps

1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

None while deferred.

## Open questions

None while deferred.
