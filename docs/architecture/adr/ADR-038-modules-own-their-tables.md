# ADR-038: Modules are Django apps that own their tables

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. Every model lives in the shared `db` app.

## Context

One `db` app maps every table, and the user model is imported across a large part of the codebase.
A map of who writes each table shows several writer areas per shared table: `user_role_link`,
for example, is written from 24 functions in 16 files.

## Options considered

- **One app per module, with each table mapped for writes by exactly one module.**
- **Keep the single `db` app, with modules holding logic only:** ownership stays invisible, and
  Django foreign keys keep everything coupled.
- **One app per module with Django `ForeignKey`s across modules:** easy joins, but ORM cascades
  leak and extraction becomes impossible.

## Decision

1. **The owner maps its tables** in `modules/<m>/data/models.py` (`managed = False`, mirroring
   the DDL). Only the owner writes them.
2. **During migration,** the legacy `db` model for a moved table may remain for legacy readers.
   Legacy writers of a moved table are listed in an allowlist that must reach zero by the
   module's cut-over.
3. **Cross-module references** are plain id fields in Python, never `ForeignKey`, and an AST
   check enforces this. The DDL keeps the foreign key for integrity.
4. **Reads across modules** go through the owner's batch-capable selectors in `public.py`. These
   return dataclasses or TypedDicts, never models or querysets.
5. **`public.py`** holds functions and DTOs only, and every export has a docstring. More than 25
   exports triggers an architecture review.
6. **Layering** is `services/` and `selectors/`, with a thin `domain/` of pure functions and value
   objects where a state machine exists. There is no repository layer over the ORM except where
   it pays, such as the ledger's append-and-compare.
7. **Tables move on demand:** when a roadmap item changes them, or when they sit on a money,
   authorization or identity path. Everything else stays in `db/` behind the legacy contracts.
   "Done" does not mean every table has moved.

### Refinements (2026-11-21)

- DTOs are defined in `contracts.py`; `public.py` imports them for its signatures and holds functions only. Events are exported from `contracts.py` only.

## Consequences

- Ownership becomes visible in code and in database grants.
- A join across modules becomes two queries or a read model.
- Legacy code keeps working throughout.

## Revisit when

- A module needs a second persistence backend.

## Related ADRs

[ADR-001](ADR-001-domain-oriented-modular-monolith.md), [ADR-003](ADR-003-one-owner-per-table.md), [ADR-016](ADR-016-architecture-enforced-by-automation.md), [ADR-017](ADR-017-one-layered-module-structure.md)
