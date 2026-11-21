# ADR-052: Privacy, minors and erasure (DPDP)

Status: Accepted (new on 2026-11-21; flagged for legal counsel)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. There are no consent records, age gate or erasure command.

## Context

India's Digital Personal Data Protection Act 2023 and the DPDP Rules 2025 phase in obligations:
- consent;
- purpose limitation;
- data-principal rights (access, correction and erasure);
- breach notification;
- retention limits;
- verifiable parental consent for users under 18.

The core obligations apply from about May 2027. The CERT-In directions require incident reporting
within 6 hours and 180 days of logs kept in India. Erasure must coexist with an append-only ledger
and an audit trail. This record states the design. It is not legal advice.

## Options considered

- **Hard delete.**
- **Pseudonymise:** keep the ledger, and delete or blank the personal data.
- **Crypto-shredding with per-user keys.**

## Decision

1. **Subject identifiers.**
   - The user UUID is the pseudonymous subject id.
   - Ledger, audit and outbox payloads hold UUIDs and non-personal facts only. A test checks
     payload keys against a list of personal-data fields.
   - Crypto-shredding is therefore unnecessary.
2. **Erasure:**
   - anonymises the personal-data columns on `user`;
   - deletes personal-data side tables after their retention periods;
   - keeps ledger and audit rows.

   Users are never hard-deleted. The application's database user has no DELETE grant on `user` or
   on the history tables, and history foreign keys move to `RESTRICT` as each module moves.
3. **Consent records** store purpose, notice version, timestamp and channel. Users see them at
   signup and whenever they change.
4. **Minors:**
   - Date of birth is required when the organisation type is a school, or when the age is unknown.
   - Under 18 leads to a verifiable parental-consent flow.
   - Until that flow exists, under-18 signups are held, unless counsel confirms an exemption
     applies.
   - Accounts created before the age gate are reviewed with counsel.
5. **Rights:**
   - export, as an asynchronous job;
   - correction, through the profile;
   - erasure, as an audited workflow with a 30-day hold.
6. **Breach response:** a runbook with both clocks (6 hours and 72 hours), and a processor
   inventory.
7. **Retention schedule,** set with counsel: logs, login attempts and donation records each get
   their statutory or advised period.

### Refinements (2026-11-21)

- This work ships by the 13 April 2027 release train at the latest, because the obligations start inside the exam caution window.
- Logs of record are kept 400 days in ap-south-1 ([ADR-012](ADR-012-opentelemetry-sentry-json-logs.md)) unless counsel shortens it.
- History foreign keys move to `RESTRICT` only after both account-deletion paths (`api/dashboard/profile/profile_view.py` and `api/dashboard/user/dash_user_views.py`, both `delete`) anonymise instead of deleting. Until then, new history tables, such as the karma ledger, use `CASCADE` like the tables they replace.

## Consequences

- Rights requests and erasure don't break ledger integrity.
- Some product flows change, such as age capture and consent screens, and need client releases.

## Revisit when

- Counsel gives an opinion, and at a commencement review one month before the obligations apply.

## Related ADRs

[ADR-003](ADR-003-one-owner-per-table.md), [ADR-004](ADR-004-karma-ledger.md), [ADR-012](ADR-012-opentelemetry-sentry-json-logs.md), [ADR-032](ADR-032-audit-trail-and-retention.md)
