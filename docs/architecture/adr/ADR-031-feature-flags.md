# ADR-031: Feature flags: the persisted flag store is the single mechanism

Status: Replaced on 2026-11-21 (the earlier decision to use OpenFeature is withdrawn; this record states the replacement)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Toggles live in `system_setting` rows, configuration tables and environment settings.

## Context

Several flag mechanisms exist side by side: settings rows, configuration tables, admin toggles
and environment switches. A single persisted, audited flag store in `building_blocks/flags`
(tables `feature_flag` and `feature_flag_change`) can replace them all. It provides:
- murmur bucketing;
- declared flags, each with an owner and an expiry;
- safe defaults when the store is unavailable.

## Options considered

- **Wrap the flag store in OpenFeature:** adds a dependency and an indirection with no current
  consumer.
- **The persisted flag store as the single mechanism.**
- **Unleash, Flagsmith or GrowthBook:** each adds a datastore.

## Decision

- **The persisted flag store in `building_blocks/flags` is the only flag mechanism.**
- Existing toggles migrate into it. A toggle that guards a write gets a fail-closed default.
- Environment switches remain only for boot-time modes such as the environment name.
- **CI fails on expired release flags.**
- **Kill switches need two people** during freezes.
- **Shadow and observe modes are declared flags with an owner and a `flip_by` date.** CI fails
  when the date passes and the flag is still in shadow, so a safeguard can't stay off
  indefinitely.

### Refinements (2026-11-21)

- A flag that gates the removal of existing behaviour defaults to today's behaviour, with an expiry date.
- Schedule flags (`schedule.<name>`) default to on outside production and off in production, so production needs explicit enablement.

## Consequences

- One audited mechanism, with no new infrastructure.
- If a vendor is ever needed, only the store adapter changes.

## Revisit when

- There are more than 200 flags, or experimentation statistics are needed.

## Related ADRs

[ADR-037](ADR-037-weekly-release-train.md), [ADR-043](ADR-043-redis-cache-and-state.md)
