# ADR-041: Transaction and consistency rules

Status: Accepted (new on 2026-11-21; amends ADR-022)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. Transaction use varies per view, and several `.delay()` calls run without `transaction.on_commit`.

## Context

Some legacy handlers write several rows without a transaction, and some update balances by
read-modify-write. Several services write module tables. Django runs MySQL at READ COMMITTED.
Cross-module work needs a rule that is both enforceable and practical.

## Options considered

- **Strict events only, including in legacy code.**
- **Events by default; synchronous cross-module commands each in their own transaction.**
- **Shared transactions across modules.**

## Decision

1. **One transaction per use case.**
   - Every service command is decorated with `@command(owner="<module>")`, which opens
     `atomic()`, records the owning module, and retries deadlocks at the outermost level only.
   - If a command of module B starts inside an open transaction of module A, the guard raises in
     tests and development, and logs and counts in production.
   - Legacy code may wrap a module command only from allowlisted sites. The allowlist shrinks to
     zero at the module's cut-over.
2. **Cross-module writes:**
   - by default, an outbox event that the owner applies idempotently;
   - synchronously only when the caller needs the answer now. The callee then runs its own
     transaction, before the caller opens its own, and takes an idempotency key so the sequence
     can be retried or compensated.
3. **Money:**
   - Coins are not moved by the backend: the coin economy lives in `mucoin-service`, which
     consumes integration events and never writes back ([ADR-054](ADR-054-mucoin-external-consumer.md)).
   - Donations and payments (`payments`) record provider events idempotently, keyed by the
     provider's event id.
   - No money moves across a module boundary synchronously.
4. **An early codemod** wraps every multi-row write on money and role tables in
   `transaction.atomic()`, with outbound calls moved after commit.
5. **Side effects:**
   - The outbox insert happens in the same transaction.
   - Legacy `.delay()` calls go through `safe_enqueue()`, which enqueues on commit. If the broker
     is down, it writes an outbox row instead, so a committed request never turns into an error.
   - Never send email, HTTP, push or Discord calls inside a transaction.
6. **Isolation:** READ COMMITTED. Serialisation comes from locks and constraints.
7. **Locks:**
   - `select_for_update()` only on rows the module owns, in a documented order per module;
   - `F()` expressions for counters;
   - a database `UNIQUE` constraint for every natural key used by `get_or_create`.
8. **Idempotency:** ledger keys, `Idempotency-Key` on HTTP POST, and inbox dedupe for consumers.

### Refinements (2026-11-21)

- The dormant coin columns and tables (`wallet.coin`, `mucoin_activity_log`, `mucoin_invite_log`) are frozen. No command reads or writes them for new features.
- The bot and the scheduler use the server's default isolation level, not READ COMMITTED: one more reason serialisation relies on locks and constraints.
- Event consumers run each handler as a command of the consuming module, so the transaction guard accepts the module's own consumers.

## Consequences

- Lock scopes stay small, and modules stay extractable.
- Some cross-module effects are eventually consistent.
- The guard prevents violations in tests and detects them in production.

## Revisit when

- A use case needs cross-module atomicity that a reservation or saga can't provide. That needs its
  own ADR.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-005](ADR-005-transactional-outbox.md), [ADR-022](ADR-022-no-cross-module-transactions.md), [ADR-044](ADR-044-api-standards-v1-2.md)
