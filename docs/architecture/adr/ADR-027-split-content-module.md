# ADR-027: Split the `content` grab-bag into cohesive modules

Status: Accepted (low priority)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started.

## Context

The `content` area mixes comics, media, projects, problem statements and a URL shortener. Each has
a different owner and a different reason to change.

## Options considered

- **Split by cohesion when the code moves.**
- **Keep one content module:** one owner can't own unrelated features.

## Decision

- `media`: comics and media content.
- `projects`: projects and impact projects.
- Problem statements move to `careers`.
- The URL shortener moves to `administration`.

The split happens when each part moves into a module, not as a separate project. The module
catalogue reflects the table-ownership map.

## Consequences

- Each module has one clear owner.

## Revisit when

- A part of `content` gains a second owner or a new reason to change.

## Related ADRs

[ADR-038](ADR-038-modules-own-their-tables.md)
