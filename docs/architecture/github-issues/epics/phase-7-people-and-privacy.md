# Phase 7: people and privacy

| | |
|---|---|
| Epic | phase-7-people-and-privacy |
| Phase / milestone | Phase 7: People and privacy |
| Labels | arch, phase:7, module:people, type:epic |

## What it will contain

From [ADR-052](../../adr/ADR-052-privacy-minors-erasure.md). It is flagged for legal advice; the DPDP Rules' core obligations apply from about May 2027.

- **The `people` module** owns profiles, settings, socials, consent records and erasure.
- **Consent records:** purpose, notice version, timestamp and channel, captured at signup and shown to users.
- **An age gate,** with parental consent or a held signup for users under 18, as counsel confirms.
- **Rights workflows:** export as a bulk job, correction, and erasure with a 30-day hold. Erasure anonymises personal columns and keeps ledger and audit rows.
- **Account deletion anonymises:** both delete paths (the profile and the admin user views) anonymise instead of hard-deleting, with a characterization test for each first.
- **History foreign keys** move from `CASCADE` to `RESTRICT`, table by table, outside exam periods, starting with the karma ledger's user key. This happens only after deletion anonymises.
- **A breach runbook** and a processor inventory.
- **Retention jobs** for logs and personal side tables.

## Entry conditions

- Counsel has reviewed the design.
- The signup serializer accepts the new optional fields before any client sends them.

## Exit criteria

- 100% of new signups pass the age gate.
- No account under 18 is processed without consent or a hold.
- Consent records exist for 100% of signups after enablement.
- An export is delivered within 24 hours.
- A breach tabletop exercise completes.
- Counsel signs off before the legal date.
