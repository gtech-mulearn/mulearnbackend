# Phase 4: finish the contributions cut-over

| | |
|---|---|
| Epic | phase-4-contributions-cutover |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Labels | arch, phase:4, module:contributions, type:epic |

## What it will contain

The rest of Phase 4 after the 12-week slice ([13-migration-strategy.md](../../13-migration-strategy.md)):

- **Bot switch, one command at a time:** submit, peer approval, appraisal, reversal. Each switch happens after its shadow-mode diff is explained. This is maintainer-only work in the bot's repository.
- **Revoke the bot's direct writes:** remove its INSERT, UPDATE and DELETE grants on `karma_activity_log` and `wallet`, at least 14 days after the last switch (maintainer-only).
- **The Discord reconciler** in `integrations`: a backend job with a read-only Discord credential. Every 15 minutes it reads 48 hours of task-channel history and drives the same `contributions` commands ([ADR-018](../../adr/ADR-018-channel-agnostic-contributions.md)).
- **Reconciliation pages instead of tickets** once every writer is on the ledger.
- **Events instead of direct writes** for learning-circle, intern and voucher awards: `LearningCircleMeetingReported`, `InternWorkApproved` and `VoucherRedeemed`, consumed by `contributions`.
- **Hard deletes become reversals:** removing a Discord message writes a reversal instead of deleting rows.
- **A one-time true-up** after the bot's last switch: for every user whose drift reconciliation attributes to the bot's earlier direct writes, an `adjust` entry (issue 0086) with the reason `reconciliation true-up <date>`, made by an admin and recorded per user.

## Entry conditions

- Issues 0091, 0100, 0103 and 0104 have merged and been rolled out.
- Shadow mode has run for at least 7 days, with every disagreement explained.

## Exit criteria

- Every backend karma write goes through `modules.contributions.public`: the legacy-writer allowlist for `karma_activity_log` and `wallet` holds only the frozen coin writer (the referral coin debit, [ADR-054](../../adr/ADR-054-mucoin-external-consumer.md)).
- The bot holds no write grant on `karma_activity_log` or `wallet`.
- After the true-up, ledger drift is 0 for 14 consecutive days.
- The reconciler converges a 2-hour drill gap within 15 minutes, and the heartbeat alert fires within 10 minutes in a drill.
